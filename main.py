import os
import time
import random

from dotenv import load_dotenv
from openai import (
    OpenAI,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
)

load_dotenv()

providers = [
    {
        "name": "Gemini",
        "model": "gemini-2.5-flash",
        "client": OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    },
    {
        "name": "OpenAI",
        "model": "gpt-4o-mini",
        "client": OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
    }
]


def ask_with_retry(provider, messages):
    for attempt in range(4):
        try:
            response = provider["client"].chat.completions.create(
            model=provider["model"],
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            stream=True,
            stream_options={"include_usage": True}
        )

            return response

        except (
            RateLimitError,
            APITimeoutError,
            APIConnectionError,
            InternalServerError
        ) as error:

            if attempt == 3:
                raise

            delay = 2 ** attempt

            print(f"Error: {type(error).__name__}")
            print(f"Retrying in {delay} seconds...")

            time.sleep(delay)




def ask_ai(messages, on_event=None):
    for provider in providers:
        try:
            print(f"\nTrying {provider['name']}...")

            stream = ask_with_retry(provider, messages)

            answer = ""
            usage = None

            print("\nAssistant: ", end="", flush=True)

            for chunk in stream:
                if chunk.usage is not None:
                    usage = chunk.usage

                if chunk.choices:
                    content = chunk.choices[0].delta.content

                    if content:
                        print(content, end="", flush=True)
                        answer += content
                        if on_event is not None:
                            on_event({"type": "chunk", "content": content})

            print()

            if usage:
                print("\n--- Token Usage ---")
                print("Prompt tokens:", usage.prompt_tokens)
                print("Completion tokens:", usage.completion_tokens)
                print("Total tokens:", usage.total_tokens)

            print("Answered by:", provider["name"])

            return answer

        except Exception as error:
            print(f"\n{provider['name']} failed: {error}")
            print("Trying the next provider...")
            if on_event is not None:
                on_event({"type": "reset"})

    print("Both providers failed.")
    return None





def main():
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        }
    ]

    print("Welcome to Multi-Model Chatbot!")
    print("Type 'exit' to stop.")

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() == "exit":
            print("Goodbye!")
            break

        if not user_input:
            continue

        messages.append({
            "role": "user",
            "content": user_input
        })

        answer = ask_ai(messages)

        if answer is not None:
            print("\nAssistant:", answer)

            messages.append({
                "role": "assistant",
                "content": answer
            })
        else:
            messages.pop()

main()
