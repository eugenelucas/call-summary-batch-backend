
from core.llm import client
from langchain_core.prompts import ChatPromptTemplate

async def auto_correct_text(text: str) -> str:
    """
    Call Azure OpenAI for auto correction.
    Returns corrected transcript.
    """


    system_prompt = """
    You are a careful, minimal copy editor for live transcripts.
    - Fix grammar, punctuation, casing, and obvious ASR errors.
    - Do NOT change meaning or add/remove facts.
    - Preserve line breaks and speaker turns.
    - Also remove common disfluencies (um/umm/uh/er/erm/eh/hmm/mmm/mm/ah, "uh-huh"/"mm-hmm",
    and the phrases "I mean" and "you know" when they appear as fillers).
    Return ONLY the corrected text.
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "{question}"),
        ]
    )


    chain = prompt | client

    response = chain.invoke({"question": text})
    return response.content    
    

    

    