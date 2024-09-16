import chainlit as cl
import openai
from dotenv import load_dotenv
import os
from langsmith import traceable
from langsmith.wrappers import wrap_openai
import requests

from bs4 import BeautifulSoup

url = "https://www.nytimes.com/wirecutter/reviews/best-coffee-maker/"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")
text = [p.text for p in soup.find_all("p")]
full_text = "\n".join(text)

from prompts import SYSTEM_PROMPT_FOR_REVIEWS

load_dotenv()
# api_key = os.getenv("OPENAI_API_KEY")

api_key = os.getenv("RUNPOD_API_KEY")
runpod_serverless_id = os.getenv("RUNPOD_SERVERLESS_ID")

endpoint_url = "https://api.openai.com/v1"
# endpoint_url = f"https://api.runpod.ai/v2/{runpod_serverless_id}/openai/v1"

# client = openai.AsyncClient(api_key=api_key, base_url=endpoint_url)


# TODO: Change the prompt to add coffee machine recommender. Make sure to do the langchain thing




client = wrap_openai(openai.AsyncClient())
# https://platform.openai.com/docs/models/gpt-4o
model_kwargs = {
    "model": "chatgpt-4o-latest",
    "temperature": 0.2,
    "max_tokens": 500
}

# model_kwargs = {
#     "model": "mistralai/Mistral-7B-Instruct-v0.3",
#     "temperature": 0.3,
#     "max_tokens": 500
# }

# @cl.on_message
async def on_message_raw(message: cl.Message):
    # Your custom logic goes here...

    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": message.content}],
        **model_kwargs
    )

    # https://platform.openai.com/docs/guides/chat-completions/response-format
    response_content = response.choices[0].message.content

    await cl.Message(
        content=response_content,
    ).send()


# @cl.on_message
async def on_message_streaming(message: cl.Message):
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(messages=[{"role": "user", "content": message.content}],
                                                  stream=True, **model_kwargs)
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)

    await response_message.update()



@cl.on_message
@traceable
async def on_message_stream_with_history(message: cl.Message):
    # Maintain an array of messages in the user session
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})

    response_message = cl.Message(content="")

    if (not message_history or message_history[0].get("role") != "system"):
            system_prompt_content = SYSTEM_PROMPT_FOR_REVIEWS.format(website_text=full_text)
            message_history.insert(0, {"role": "system", "content": system_prompt_content})


    await response_message.send()

    # Pass in the full message history for each request
    stream = await client.chat.completions.create(messages=message_history,
                                                  stream=True, **model_kwargs)
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)

    await response_message.update()

    # Record the AI's response in the history
    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)


import base64

# @cl.on_message
# async def on_message_with_image(message: cl.Message):
#     # Maintain an array of messages in the user session
#     message_history = cl.user_session.get("message_history", [])

#     # Processing images exclusively
#     images = [file for file in message.elements if "image" in file.mime] if message.elements else []
#     if images:
#         # Read the first image and encode it to base64
#         with open(images[0].path, "rb") as f:
#             base64_image = base64.b64encode(f.read()).decode('utf-8')
#         message_history.append({
#             "role": "user",
#             "content": [
#                 {
#                     "type": "text",
#                     "text": message.content if message.content else "What’s in this image?"
#                 },
#                 {
#                     "type": "image_url",
#                     "image_url": {
#                         "url": f"data:image/jpeg;base64,{base64_image}"
#                     }
#                 }
#             ]
#         })
#     else:
#         message_history.append({"role": "user", "content": message.content})

#     response_message = cl.Message(content="")
#     await response_message.send()

#     # Pass in the full message history for each request
#     stream = await client.chat.completions.create(messages=message_history,
#                                                   stream=True, **model_kwargs)
#     async for part in stream:
#         if token := part.choices[0].delta.content or "":
#             await response_message.stream_token(token)

#     await response_message.update()

#     # Record the AI's response in the history
#     message_history.append({"role": "assistant", "content": response_message.content})
#     cl.user_session.set("message_history", message_history)
