from ninja import NinjaAPI, File, UploadedFile, Form
from gradio_client import Client, handle_file
from PIL import Image

# from decouple import config     #if using your own token

from .models import ImageDetection

import pathlib

import os
import re


api = NinjaAPI()

def normalize_coordinates(coord: str, img_x, img_y):
    pattern = r'<loc(\d+)>'
    matches = re.findall(pattern, coord)
    # The coordinates also need to be normalized i.e., divide by 1024 and then multiple by height, width of the original image.
    
    numbers = [int(match) for match in matches]
    numbers[0] = int((numbers[0] / 1024) * img_y)
    numbers[1] = int((numbers[1] / 1024) * img_x)
    numbers[2] = int((numbers[2] / 1024) * img_y)
    numbers[3] = int((numbers[3] / 1024) * img_x)
    return numbers

@api.post('/detect')
def detect(request, prompt: Form[str], image: File[UploadedFile], width: Form[int], height: Form[int]):

    print("Width: ", width)
    print("Height: ", height)
    print("Original image: ", str(image))
    print("Prompt: ", prompt)
    client = Client("big-vision/paligemma")
    prompt_obj = ImageDetection.objects.create(
        prompt=prompt,
        image=image
    )
    cwd = pathlib.Path(os.getcwd())
    image_path = pathlib.Path(prompt_obj.image.url[1:]) #skipping the forward slash so pathlib doesnt consider it an absolute url
    img_path = pathlib.Path(cwd , image_path)
    media_path = os.getcwd() + '/media/images/'

    # Resize image with width, height parameters.
    print(image)
    img = Image.open(img_path)
    img = img.convert('RGB')
    resized_img = img.resize((width, height), Image.Resampling.LANCZOS)
    resized_img_path = media_path + 'resized_' + str(image)
    print("Image path:")
    print(resized_img_path)
    resized_img.save(resized_img_path)

    result = client.predict(
    handle_file(resized_img_path),
    prompt,
    "paligemma-3b-mix-224", # str in 'Prompt' Textbox component # Literal[] in 'Model' Dropdown component
    "greedy", # Literal['greedy', 'nucleus(0.1)', 'nucleus(0.3)', 'temperature(0.5)'] in 'Decoding' Dropdown component
    api_name="/compute"
    )

    print(result)
    

    # Delete images after processing.
    [os.remove(os.path.join(media_path, f)) for f in os.listdir(media_path) if os.path.isfile(os.path.join(media_path, f))]
    
    # print(f"{result=}")
    data = result[0]["value"]
    img_x = result[2]["width"]
    img_y = result[2]["height"]

    print("img_x: ", img_x)
    print("img_y: ", img_y)
    """
    # create a list of objects detected
    [
        {
            "object": "car",
            "coordinates": [y1 x1 y2 x2]
        }
    ]
    """
    container = []
    errors = []
    print(data)
    if len(data) == 0:
        temp = {}
        temp["error"] = "Detection not found."
        temp["coordinates"] = ''
        errors.append(temp)
        print("Error in detection:")
        abc = {"result" : errors}
        print(abc)
        return {"result": errors}
    else:
        for object in data:
            temp = {}
            temp["label"] = object["class_or_confidence"]
            temp['coordinates'] = normalize_coordinates(object["token"], img_x, img_y)
            container.append(temp)
            print("Success")
            return {"result": container}
            
    
