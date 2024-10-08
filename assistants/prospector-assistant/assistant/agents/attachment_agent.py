import base64
import io
import logging
from pathlib import Path
from typing import Annotated, Any

import fitz
import pymupdf4llm
from docx import Document
from docx.document import Document as _Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from openai.types import chat
from PIL import Image
from pydantic import BaseModel, Field
from semantic_workbench_api_model.workbench_model import File
from semantic_workbench_assistant.assistant_app import (
    ConversationContext,
    FileStorageContext,
)
from semantic_workbench_assistant.config import UISchema
from semantic_workbench_assistant.storage import (
    read_model,
    read_models_in_dir,
    write_model,
)

logger = logging.getLogger(__name__)


#
# region Models
#


class AttachmentAgentConfigModel(BaseModel):
    context_description: Annotated[
        str,
        Field(
            description="The description of the context for general response generation.",
        ),
        UISchema(widget="textarea"),
    ] = (
        "These attachments were provided for additional context to accompany the conversation. Consider any rationale"
        " provided for why they were included."
    )

    include_in_response_generation: Annotated[
        bool,
        Field(
            description=(
                "Whether to include the contents of attachments in the context for general response generation."
            ),
        ),
    ] = True


class Attachment(BaseModel):
    filename: str
    content: str
    metadata: dict[str, Any]
    markdown_content: str | None = None
    extracted_images: list[str] = []


# endregion


#
# region Agent
#


attachment_tag = "ATTACHMENT"
filename_tag = "FILENAME"
content_tag = "CONTENT"
image_tag = "IMAGE"


class AttachmentAgent:
    @staticmethod
    async def create_or_update_attachment_from_file(
        context: ConversationContext, file: File, metadata: dict[str, Any]
    ) -> None:
        """
        Create or update an attachment from the given file.

        This method processes the file content, converts it to markdown if applicable,
        and extracts images from PDF and DOCX files.

        Args:
            context (ConversationContext): The context of the conversation.
            file (File): The file to process.
            metadata (dict[str, Any]): Additional metadata for the attachment.

        Raises:
            Exception: If there's an error processing the file.
        """
        filename = file.filename

        try:
            # get the content of the file and convert it to a string and markdown
            content, markdown_content, extracted_images = await _file_to_str_and_markdown(context, file)

            # see if there is already an attachment with this filename
            attachment = read_model(_get_attachment_storage_path(context, filename), Attachment)
            if attachment:
                # if there is, update the content
                attachment.content = content
                attachment.markdown_content = markdown_content
                attachment.extracted_images = extracted_images
            else:
                # if there isn't, create a new attachment
                attachment = Attachment(
                    filename=filename,
                    content=content,
                    metadata=metadata,
                    markdown_content=markdown_content,
                    extracted_images=extracted_images,
                )

            write_model(_get_attachment_storage_path(context, filename), attachment)
        except Exception as e:
            logger.exception(f"Error processing attachment {filename}: {str(e)}")
            raise

    @staticmethod
    def delete_attachment_for_file(context: ConversationContext, file: File) -> None:
        """
        Delete the attachment for the given file.
        """

        filename = file.filename
        _get_attachment_storage_path(context, filename).unlink(missing_ok=True)

    @staticmethod
    def generate_attachment_messages(
        context: ConversationContext,
        filenames: list[str] | None = None,
        ignore_filenames: list[str] | None = None,
    ) -> list[chat.ChatCompletionMessageParam]:
        """
        Generate systems messages for each attachment that includes the filename and content.

        In the case of images, the content will be a data URI, other file types will be included as text.

        If filenames are provided, only attachments with those filenames will be included.

        If ignore_filenames are provided, attachments with those filenames will be excluded.

        This method now includes support for markdown content and extracted images.

        Args:
            context (ConversationContext): The context of the conversation.
            filenames (list[str] | None): List of filenames to include. If None, include all.
            ignore_filenames (list[str] | None): List of filenames to ignore.

        Returns:
            list[chat.ChatCompletionMessageParam]: List of messages for each attachment.
        """

        # get all attachments and exit early if there are none
        attachments = read_models_in_dir(_get_attachment_storage_path(context), Attachment)
        if not attachments:
            return []

        # process each attachment
        messages = []
        for attachment in attachments:
            # if filenames are provided, only include attachments with those filenames
            if filenames and attachment.filename not in filenames:
                continue

            # if ignore_filenames are provided, exclude attachments with those filenames
            if ignore_filenames and attachment.filename in ignore_filenames:
                continue

            content_to_use = attachment.markdown_content or attachment.content

            # if the content is a data URI, include it as an image type within the message content
            # NOTE: newer versions of the API only allow messages with the user role to include images
            if content_to_use.startswith("data:image/"):
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"<{attachment_tag}><{filename_tag}>{attachment.filename}</{filename_tag}><{image_tag}>",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": content_to_use,
                            },
                        },
                        {
                            "type": "text",
                            "text": f"</{image_tag}></{attachment_tag}>",
                        },
                    ],
                })
            else:
                # otherwise, include the content as text within the message content
                content_details = f"<{filename_tag}>{attachment.filename}</{filename_tag}><{content_tag}>{content_to_use}</{content_tag}>"

                messages.append({
                    "role": "system",
                    "content": f"<{attachment_tag}>{content_details}</{attachment_tag}>",
                })

            # Add extracted images
            for image_path in attachment.extracted_images:
                try:
                    with open(image_path, "rb") as image_file:
                        image_data = base64.b64encode(image_file.read()).decode("utf-8")
                        data_uri = f"data:image/png;base64,{image_data}"
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"<{attachment_tag}><{filename_tag}>{Path(image_path).name}</{filename_tag}><{image_tag}>",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_uri,
                                },
                            },
                            {
                                "type": "text",
                                "text": f"</{image_tag}></{attachment_tag}>",
                            },
                        ],
                    })
                except Exception as e:
                    logger.error(f"Error processing extracted image {image_path}: {str(e)}")

        return messages

    @staticmethod
    def reduce_attachment_payload_from_content(value: Any) -> Any:
        """
        Reduce the content of any attachment in the payload to a smaller size.

        This method is intended to be used with the debug metadata in the parent assistant that
        uses this agent to reduce the size of the content of the attachments in the payload.

        The content will be reduced to the first and last `head_tail_length` characters, with a
        placeholder in the middle.
        """

        # define the length of the head and tail of the content to keep and the placeholder to use in the middle
        head_tail_length = 40
        placeholder = "<REDUCED_FOR_DEBUG_OUTPUT/>"

        # inspect the content and look for the attachment tags
        # there are two types of content that we need to handle: text and image
        # if the content is an image, we will be reducing the image_url.url value
        # if the content is text, we will be reducing the text value if it contains the attachment tag

        # start by checking if this is a string or a list of dictionaries
        if isinstance(value, str):
            # if this is a string, we can assume that this is a text content
            # we will be reducing the text value if it contains the attachment tag
            if attachment_tag in value:
                # just reduce within the content_tag, but still show the head/tail in there
                start_index = value.find(f"<{content_tag}>") + len(f"<{content_tag}>")
                end_index = value.find(f"</{content_tag}>")
                if start_index != -1 and end_index != -1:
                    return (
                        value[: start_index + head_tail_length]
                        + f"...{placeholder}..."
                        + value[end_index - head_tail_length :]
                    )
        elif isinstance(value, list):
            # if this is a list, check to see if it contains dictionaries
            # and if they contain the attachment tag
            # if so, look for and reduce the image_url.url value
            is_attachment = False
            for item in value:
                if isinstance(item, dict):
                    if "text" in item and attachment_tag in item["text"]:
                        is_attachment = True
                        break
            if is_attachment:
                # reduce the image_url.url value
                for item in value:
                    if isinstance(item, dict) and "image_url" in item:
                        item["image_url"]["url"] = item["image_url"]["url"][:head_tail_length] + f"...{placeholder}"
            return value

        # if the content is not an attachment, return the original value
        return value


# endregion


#
# region Helpers
#


def _get_attachment_storage_path(context: ConversationContext, filename: str | None = None) -> Path:
    """
    Get the path where attachments are stored.
    """
    path = FileStorageContext.get(context).directory / "attachments"
    if filename:
        path /= filename
    return path


async def _raw_content_from_file(context: ConversationContext, file: File) -> bytes:
    """
    Read the content of the file with the given filename.
    """
    raw_content = context.read_file(file.filename)
    content = b""
    async with raw_content as f:
        async for chunk in f:
            content += chunk
    return content


def _image_raw_content_to_str(raw_content: bytes, filename: str) -> str:
    """
    Convert the raw content of an image file to a data URI.
    """
    try:
        data = base64.b64encode(raw_content).decode("utf-8")
        image_type = f"image/{filename.split('.')[-1]}"
        data_uri = f"data:{image_type};base64,{data}"
        return data_uri
    except Exception as e:
        message = f"error converting image {filename} to data URI: {e}"
        logger.exception(message)
        raise Exception(message)


def _unknown_raw_content_to_str(raw_content: bytes, filename: str) -> str:
    """
    Convert the raw content of an unknown file type to a string.
    """
    try:
        return raw_content.decode("utf-8")
    except Exception as e:
        message = f"error converting unknown file type {filename} to text: {e}"
        logger.exception(message)
        raise Exception


async def _file_to_str_and_markdown(context: ConversationContext, file: File) -> tuple[str, str | None, list[str]]:
    """
    Convert the content of the file to a string and markdown (if applicable), and extract images.

    Args:
        context (ConversationContext): The context of the conversation.
        file (File): The file to process.

    Returns:
        tuple[str, str | None, list[str]]: A tuple containing the original content,
        markdown content (if applicable), and a list of extracted image paths.
    """
    filename = file.filename
    raw_content = await _raw_content_from_file(context, file)

    filename_extension = filename.split(".")[-1].lower()

    content = ""
    markdown_content = None
    extracted_images = []

    logger.info(f"Processing file {filename} with extension {filename_extension}")

    if filename_extension == "pdf":
        content, markdown_content, extracted_images = _pdf_to_markdown(raw_content, filename, context)
    elif filename_extension == "docx":
        content, markdown_content, extracted_images = _docx_to_markdown(raw_content, filename, context)
    elif filename_extension in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "tif"]:
        content = _image_raw_content_to_str(raw_content, filename)
    else:
        content = _unknown_raw_content_to_str(raw_content, filename)

    return content, markdown_content, extracted_images


def _pdf_to_markdown(raw_content: bytes, filename: str, context: ConversationContext) -> tuple[str, str, list[str]]:
    """
    Convert PDF content to markdown and extract images.

    Args:
        raw_content (bytes): The raw content of the PDF file.
        filename (str): The name of the file.
        context (ConversationContext): The context of the conversation.

    Returns:
        tuple[str, str, list[str]]: A tuple containing the original content,
        markdown content, and a list of extracted image paths.
    """
    try:
        base_name = sanitize_filename(Path(filename).stem)
        image_folder = _get_attachment_storage_path(context) / f"{base_name}_pdf_images"
        # Ensure the entire path exists
        image_folder.parent.mkdir(parents=True, exist_ok=True)
        image_folder.mkdir(exist_ok=True)

        logger.info(f"Converting PDF {filename} to markdown")
        # Create a PyMuPDF document object from the raw content
        with fitz.open(stream=raw_content, filetype="pdf") as pdf_file:
            md_text = pymupdf4llm.to_markdown(pdf_file, write_images=True, image_path=str(image_folder), dpi=150)

        extracted_images = list(image_folder.glob("*.png"))
        logger.info(f"Extracted {len(extracted_images)} images from PDF {filename}")
        return raw_content.decode("utf-8", errors="ignore"), md_text, [str(img) for img in extracted_images]
    except Exception as e:
        logger.exception(f"Error converting PDF {filename} to Markdown: {e}")
        return raw_content.decode("utf-8", errors="ignore"), "", []


def _docx_to_markdown(raw_content: bytes, filename: str, context: ConversationContext) -> tuple[str, str, list[str]]:
    """
    Convert DOCX content to markdown and extract images.

    Args:
        raw_content (bytes): The raw content of the DOCX file.
        filename (str): The name of the file.
        context (ConversationContext): The context of the conversation.

    Returns:
        tuple[str, str, list[str]]: A tuple containing the original content,
        markdown content, and a list of extracted image paths.
    """
    try:
        base_name = sanitize_filename(Path(filename).stem)
        image_folder = _get_attachment_storage_path(context) / f"{base_name}_docx_images"
        # Ensure the entire path exists
        image_folder.parent.mkdir(parents=True, exist_ok=True)
        image_folder.mkdir(exist_ok=True)

        logger.info(f"Converting DOCX {filename} to markdown")
        with io.BytesIO(raw_content) as docx_file:
            doc = Document(docx_file)

        markdown_content = ""
        extracted_images = []
        image_count = 0

        for block in _iter_block_items(doc):
            if isinstance(block, Paragraph):
                if block.style and block.style.name:
                    if block.style.name.startswith("Heading"):
                        level = int(block.style.name[-1])
                        markdown_content += f"{'#' * level} {block.text}\n\n"
                    elif block.style.name.startswith("Title"):
                        markdown_content += f"{'#'} {block.text}\n\n"
                else:
                    markdown_content += f"{block.text}\n\n"
                for run in block.runs:
                    image_count += 1
                    image_path = _extract_images_from_run(run, doc, image_folder, image_count)
                    if image_path:
                        extracted_images.append(str(image_path))
                        markdown_content += f"![Image {image_count}]({image_path})\n\n"

            elif isinstance(block, Table):
                markdown_table = "| " + " | ".join(cell.text for cell in block.rows[0].cells) + " |\n"
                markdown_table += "| " + " | ".join("---" for _ in block.rows[0].cells) + " |\n"
                for row in block.rows[1:]:
                    markdown_table += "| " + " | ".join(cell.text for cell in row.cells) + " |\n"
                markdown_content += markdown_table + "\n"

        logger.info(f"Extracted {len(extracted_images)} images from DOCX {filename}")
        return raw_content.decode("utf-8", errors="ignore"), markdown_content, extracted_images
    except Exception as e:
        logger.exception(f"Error converting DOCX {filename} to Markdown: {e}")
        return raw_content.decode("utf-8", errors="ignore"), "", []


def _iter_block_items(parent):
    """
    Generate a reference to each paragraph and table child within *parent*,
    in document order.

    Args:
        parent: The parent element to iterate over.

    Yields:
        Either a Paragraph or Table object.
    """
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("Expected a Document or _Cell object")

    for child in parent_elm.iterchildren():  # type: ignore
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _extract_images_from_run(run, doc, image_folder, image_count):
    """
    Extract images from a run in a DOCX file.

    Args:
        run: The run to extract images from.
        doc: The Document object.
        image_folder (Path): The folder to save extracted images.
        image_count (int): The current image count.

    Returns:
        Path | None: The path of the extracted image, or None if no image was extracted.
    """
    for element in run._r.getchildren():
        if element.tag.endswith("drawing"):
            for child in element.iter():
                if child.tag.endswith("blip"):
                    embed = child.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                    if embed:
                        image_part = doc.part.related_parts[embed]
                        image_bytes = image_part.blob
                        image_filename = f"image_{image_count}.png"
                        image_path = image_folder / image_filename

                        with Image.open(io.BytesIO(image_bytes)) as img:
                            img.save(image_path, "PNG")

                        return image_path
    return None


def sanitize_filename(filename):
    """Replace spaces with underscores in the filename."""
    return filename.replace(" ", "_")


# endregion
