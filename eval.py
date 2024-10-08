from langsmith.evaluation import evaluate, LangChainStringEvaluator
from langsmith.schemas import Run, Example
from openai import OpenAI
import json


from langsmith.wrappers import wrap_openai
from langsmith import traceable

client = wrap_openai(OpenAI())

# @traceable
def prompt_compliance_evaluator(run: Run, example: Example) -> dict:



    inputs = example.inputs["messages"]
    outputs = example.outputs

    message_history = []


    system_prompt = None
    for i in inputs:
        if i and i['data']['role'] == 'system':
            system_prompt = i['data']['content']

        if system_prompt:
            message_history.append(i)

    # Extract system prompt

    # # Extract message history
    # message_history = []
    # for msg in inputs:
    #     if msg['type'] in ['human', 'ai']:
    #         message_history.append({
    #             "role": "user" if msg['type'] == 'human' else "assistant",
    #             "content": msg['data']['content']
    #         })

    # Extract latest user message and model output
    latest_message = message_history[-1]['data']['content'] if message_history else ""
    model_output = outputs and outputs.get('data') and outputs.get('data').get('content') and outputs['data']['content']

    evaluation_prompt = f"""
    System Prompt: {system_prompt}

    Message History:
    {json.dumps(message_history, indent=2)}

    Latest User Message: {latest_message}

    Model Output: {model_output}

    Based on the above information, evaluate the model's output for compliance with the system prompt and context of the conversation.
    Provide a score from 0 to 10, where 0 is completely non-compliant and 10 is perfectly compliant.
    Also provide a brief explanation for your score.

    Inquisitiveness, on a scale of 0 to 10, how inquisitive is the model's response?

    Respond in the following JSON format:
    {{
        "score": <int>,
        "inquisitiveness": <int>,
        "explanation": "<string>"
    }}
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant tasked with evaluating the compliance of model outputs to given prompts and conversation context."},
            {"role": "user", "content": evaluation_prompt}
        ],
        temperature=0.2
    )

    try:
        result = json.loads(response.choices[0].message.content)
        return {
            "key": "prompt_compliance",
            "score": result["score"] / 10,  # Normalize to 0-1 range
            "reason": result["explanation"]
        }
    except json.JSONDecodeError:
        return {
            "key": "prompt_compliance",
            "score": 0,
            "reason": "Failed to parse evaluator response"
        }

# The name or UUID of the LangSmith dataset to evaluate on.
data = "Week1 Homework"

# A string to prefix the experiment name with.
experiment_prefix = " Week1 Homework prompt compliance"

# List of evaluators to score the outputs of target task
evaluators = [
    prompt_compliance_evaluator
]

# Evaluate the target task
results = evaluate(
    lambda inputs: inputs,
    data=data,
    evaluators=evaluators,
    experiment_prefix=experiment_prefix,
)

print(results)
