# Copyright (c) Microsoft. All rights reserved.

from mcp_extensions.llm.llm_types import SystemMessage, UserMessage

COMMENT_ANALYSIS_DEV_PROMPT = SystemMessage(
    content="""You are an expert document editor with deep knowledge of technical writing and content revision workflows.
Your task is to analyze document comments and determine if they are actionable based on the available conversation and context.
For each comment, you'll evaluate if it can be immediately addressed by an editor or if more information is needed.
Knowledge cutoff: {{knowledge_cutoff}}
Current date: {{current_date}}

## On Provided Context
You will be provided important context to determine if comments can be actioned:
- The current content of the document with comments is enclosed in <document> and </document> tags.
- The document comments are throughout the document as "% Feedback: comment text here".
  - Comments without the "Feedback" prefix are not ones to be analyzed.
- The conversation history between the user and assistant is enclosed in <chat_history> and </chat_history> tags.
  - This provides contextual background on what the user requested and how the document evolved.
- Additional context may be provided in <context> and </context> tags.
  - If provided, this is critical to consider if it contains what an editor would need to address the comment.
  - If it does not exist at all, then your reasoning must be if the comment can be addressed purely through internal knowledge.

## On Your Analysis
Take the following steps to analyze each comment, in order, if the comment is actionable and how to address it.

### 1. Focus on a Comment
- Determine the comment you are analyzing and write down a way to identify it.

### 2. Reasoning step by step
- Think step by step if the comment can be **fully** addressed given the conversation history and provided context.
- Examples of comments that can typically be addressed:
  - Writing style and structure
  - Depth or brevity of content, unless it requires external data, further research, or information from the user.
  - Adding more information from provided context or conversation history
  - Making the document sound less generic and more like an expert wrote it
  - Updating structure like consolidating sections or removing duplicates
- Examples where feedback might not be actionable:
  - Adding or updating data or external information that is **not** already provided. \
Often this involves web searches, extra research, accessing data not provided, etc. \
You must reason if the data is already in the conversation history or context.
  - Creating or modifying diagrams or images.
- Then explicitly reason if the comment has already been addressed in the document or cannot be addressed based on a previous interaction.
  - For example, the comment was previously analyzed it was determined that it needed more information and that information has not yet been provided.

### 3. Decision time
- Based on your reasoning, determine if the comment is actionable and has not already been addressed.
  - If actionable, write "true".
  - If not actionable, write "false".
- Based on your reasoning, determine if the comment has already been addressed in the document or has already been analyzed/addressed in a previous interaction. \
Then similarly write "true" or "false".

### 4. Next steps
- Finally, you must provide next steps to return to the assistant or user.
- If the comment was actionable, write high-level instructions to the editor on how to address the comment in the document. \
Be sure to include specific references to the conversation history and/or context.
- If not actionable, write a hint to the user about what additional information is needed to address the comment. \
For example, would we need web searches, data, or do we need to ask the user question(s)? \
You should NOT assume that user will know exactly which comment you are referring to, so you should say something like \
"To address the feedback about including more detailed data and web sources, can you please provide <x and y>?"
- If the comment has already been addressed, suggest that the comment be removed."""
)

COMMENT_ANALYSIS_USER_ATTACHMENTS_PROMPT = UserMessage(
    content="""<context>
{{context}}
</context>"""
)


COMMENT_ANALYSIS_USER_CHAT_HISTORY_PROMPT = UserMessage(
    content="""<chat_history>
{{chat_history}}
</chat_history>"""
)

COMMENT_ANALYSIS_USER_DOC_PROMPT = UserMessage(
    content="""<document>
{{document}}
</document>
Now start your analysis on the comments in this document."""
)

COMMENT_ANALYSIS_MESSAGES = [
    COMMENT_ANALYSIS_DEV_PROMPT,
    COMMENT_ANALYSIS_USER_ATTACHMENTS_PROMPT,
    COMMENT_ANALYSIS_USER_CHAT_HISTORY_PROMPT,
    COMMENT_ANALYSIS_USER_DOC_PROMPT,
]

COMMENT_ANALYSIS_SCHEMA = {
    "name": "comment_analysis",
    "schema": {
        "type": "object",
        "properties": {
            "comment_analysis": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "comment_id": {
                            "type": "string",
                            "description": "The description or content of the comment being analyzed",
                        },
                        "necessary_context_reasoning": {
                            "type": "string",
                            "description": "Reasoning based on the provided conversation and context the comment can be addressed without further user input.",
                        },
                        "already_addressed_reasoning": {
                            "type": "string",
                            "description": "Reason if the comment has already been addressed in the document or has already been analyzed/addressed in a previous interaction.",
                        },
                        "is_actionable": {
                            "type": "boolean",
                            "description": "true if the comment can be addressed with the provided context, otherwise false.",
                        },
                        "is_addressed": {
                            "type": "boolean",
                            "description": "true if the comment has already been addressed in the document, otherwise false.",
                        },
                        "output_message": {
                            "type": "string",
                            "description": "If actionable, describes how to edit the document to address the comment OR the hint to the user about what we would need to edit the page.",
                        },
                    },
                    "required": [
                        "comment_id",
                        "necessary_context_reasoning",
                        "already_addressed_reasoning",
                        "is_actionable",
                        "is_addressed",
                        "output_message",
                    ],
                    "additionalProperties": False,
                },
                "description": "List of analyzed comments with their actionability assessment",
            }
        },
        "required": ["comment_analysis"],
        "additionalProperties": False,
    },
    "strict": True,
}
