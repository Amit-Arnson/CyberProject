import dotenv
import os

from GroqAI.api import Model

dotenv_path = os.path.abspath("secrets.env")
dotenv.load_dotenv(dotenv_path)

api_key = os.getenv("GROQ_API_KEY")


async def summarize(comments: list[str], song_name: str):
    model = Model(key=api_key, model="llama-3.3-70b-versatile")

    try:
        message = [
            {
                "role": "system",
                "content": f"your job is to as best as possible, summarize the comments about the song \"{song_name}\"."
                           f" if you do not have any clear direction from user comments, make a guess or talk about the song."
                           f"This is for comment summarization, this means make it seem like a short summary rather than a response to a request."
                           f"try keeping the response in under 40 total words"
            },
            {
                "role": "user",
                "content": f"{comments}"
            }
        ]

        response = await model.prompt(messages=message, max_completion_tokens=60)

        return response.content
    except Exception as e:
        print(e)

