# coding=utf-8
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

# pylint: disable=protected-access

from typing import (  # pylint: disable=unused-import
    Any,
    List,
    IO,
    TYPE_CHECKING,
)
import six
from azure.core.tracing.decorator_async import distributed_trace_async
from azure.core.polling.async_base_polling import AsyncLROBasePolling
from azure.core.pipeline.policies import AzureKeyCredentialPolicy
from ._form_training_client_async import FormTrainingClient
from .._generated.aio._form_recognizer_client_async import FormRecognizerClient as FormRecognizer
from .._response_handlers import (
    prepare_receipt_result,
    prepare_content_result,
    prepare_form_result
)
from .._generated.models import AnalyzeOperationResult
from .._helpers import get_content_type, POLLING_INTERVAL, COGNITIVE_KEY_HEADER
from .._user_agent import USER_AGENT
from .._polling import AnalyzePolling
if TYPE_CHECKING:
    from azure.core.credentials import AzureKeyCredential
    from .._models import (
        USReceipt,
        FormPage,
        RecognizedForm
    )


class FormRecognizerClient(object):
    """FormRecognizerClient extracts information from forms and images into structured data.

    :param str endpoint: Supported Cognitive Services endpoints (protocol and hostname,
        for example: https://westus2.api.cognitive.microsoft.com).
    :param credential: Credentials needed for the client to connect to Azure.
        This is an instance of AzureKeyCredential if using an API key.
    :type credential: ~azure.core.credentials.AzureKeyCredential
    """

    def __init__(
            self,
            endpoint: str,
            credential: "AzureKeyCredential",
            **kwargs: Any
    ) -> None:
        self._endpoint = endpoint
        self._credential = credential
        self._client = FormRecognizer(
            endpoint=self._endpoint,
            credential=self._credential,
            sdk_moniker=USER_AGENT,
            authentication_policy=AzureKeyCredentialPolicy(credential, COGNITIVE_KEY_HEADER),
            **kwargs
        )

    def _receipt_callback(self, raw_response, receipt_locale):  # pylint: disable=unused-argument
        analyze_result = self._client._deserialize(AnalyzeOperationResult, raw_response)
        return prepare_receipt_result(analyze_result, receipt_locale)

    @distributed_trace_async
    async def begin_recognize_receipts(
            self,
            stream: IO[bytes],
            receipt_locale: str = "en-US",
            **kwargs: Any
    ) -> List["USReceipt"]:
        """Extract field text and semantic values from a given receipt document.
        The input document must be of one of the supported content types - 'application/pdf',
        'image/jpeg', 'image/png' or 'image/tiff'.

        :param stream: .pdf, .jpg, .png or .tiff type file stream.
        :type stream: stream
        :param str receipt_locale: The locale of the receipt.
            Currently only supports US sales receipts and defaults to "en-US".
        :keyword bool include_text_content: Include text lines and text content references in the result.
        :keyword str content_type: Media type of the body sent to the API.
        :return: A list of USReceipt.
        :rtype: list[~azure.ai.formrecognizer.USReceipt]
        :raises: ~azure.core.exceptions.HttpResponseError
        """
        if isinstance(stream, six.string_types):
            raise TypeError("Call begin_recognize_receipts_from_url() to analyze a receipt from a url.")

        include_text_content = kwargs.pop("include_text_content", False)
        receipt_locale = kwargs.pop("receipt_locale", "en-US")
        cls = kwargs.pop("cls", None)

        content_type = kwargs.pop("content_type", None)
        if content_type is None:
            content_type = get_content_type(stream)

        def deserialization_callback(raw_response, _, headers):  # pylint: disable=unused-argument
            return self._receipt_callback(raw_response, receipt_locale)

        callback = cls if cls else deserialization_callback
        return await self._client.analyze_receipt_async(
            file_stream=stream,
            content_type=content_type,
            include_text_details=include_text_content,
            cls=callback,
            polling=AsyncLROBasePolling(timeout=POLLING_INTERVAL, **kwargs),
            **kwargs
        )

    @distributed_trace_async
    async def begin_recognize_receipts_from_url(
            self,
            url: str,
            receipt_locale: str = "en-US",
            **kwargs: Any
    ) -> List["USReceipt"]:
        """Extract field text and semantic values from a given receipt document.
        The input document must be the location (Url) of the document to be analyzed.

        :param url: The url of the receipt.
        :type url: str
        :param str receipt_locale: The locale of the receipt.
            Currently only supports US sales receipts and defaults to "en-US".
        :keyword bool include_text_content: Include text lines and text content references in the result.
        :return: A list of USReceipt.
        :rtype: list[~azure.ai.formrecognizer.USReceipt]
        :raises: ~azure.core.exceptions.HttpResponseError
        """
        if not isinstance(url, six.string_types):
            raise TypeError("Call begin_recognize_receipts() to analyze a receipt from a stream.")

        include_text_content = kwargs.pop("include_text_content", False)
        receipt_locale = kwargs.pop("receipt_locale", "en-US")
        cls = kwargs.pop("cls", None)

        def deserialization_callback(raw_response, _, headers):  # pylint: disable=unused-argument
            return self._receipt_callback(raw_response, receipt_locale)

        callback = cls if cls else deserialization_callback
        return await self._client.analyze_receipt_async(
            file_stream={"source": url},
            include_text_details=include_text_content,
            cls=callback,
            polling=AsyncLROBasePolling(timeout=POLLING_INTERVAL, **kwargs),
            **kwargs
        )

    def _content_callback(self, raw_response, _, headers):  # pylint: disable=unused-argument
        analyze_result = self._client._deserialize(AnalyzeOperationResult, raw_response)
        return prepare_content_result(analyze_result)

    @distributed_trace_async
    async def begin_recognize_content(self, stream: IO[bytes], **kwargs: Any) -> List["FormPage"]:
        """Extract text and layout information from a given document.
        The input document must be of one of the supported content types - 'application/pdf',
        'image/jpeg', 'image/png' or 'image/tiff'.

        :param stream: .pdf, .jpg, .png or .tiff type file stream.
        :type stream: stream
        :keyword str content_type: Media type of the body sent to the API.
        :return: A list of FormPage.
        :rtype: list[~azure.ai.formrecognizer.FormPage]
        :raises: ~azure.core.exceptions.HttpResponseError
        """
        if isinstance(stream, six.string_types):
            raise TypeError("Call begin_recognize_content_from_url() to analyze a document from a url.")

        content_type = kwargs.pop("content_type", None)
        if content_type is None:
            content_type = get_content_type(stream)

        return await self._client.analyze_layout_async(
            file_stream=stream,
            content_type=content_type,
            cls=kwargs.pop("cls", self._content_callback),
            polling=AsyncLROBasePolling(timeout=POLLING_INTERVAL, **kwargs),
            **kwargs
        )

    @distributed_trace_async
    async def begin_recognize_content_from_url(self, url: str, **kwargs: Any) -> List["FormPage"]:
        """Extract text and layout information from a given document.
        The input document must be the location (Url) of the document to be analyzed.

        :param url: The url of the document.
        :type url: str
        :return: A list of FormPage.
        :rtype: list[~azure.ai.formrecognizer.FormPage]
        :raises: ~azure.core.exceptions.HttpResponseError
        """
        if not isinstance(url, six.string_types):
            raise TypeError("Call begin_recognize_content() to analyze a document from a stream.")

        return await self._client.analyze_layout_async(
            file_stream={"source": url},
            cls=kwargs.pop("cls", self._content_callback),
            polling=AsyncLROBasePolling(timeout=POLLING_INTERVAL, **kwargs),
            **kwargs
        )

    def _analyze_callback(self, raw_response, _, headers):  # pylint: disable=unused-argument
        analyze_result = self._client._deserialize(AnalyzeOperationResult, raw_response)
        return prepare_form_result(analyze_result)

    @distributed_trace_async
    async def begin_recognize_custom_forms(
            self,
            model_id: str,
            stream: IO[bytes],
            **kwargs: Any
    ) -> List["RecognizedForm"]:
        """Analyze Form.

        :param str model_id: Model identifier.
        :param stream: .pdf, .jpg, .png or .tiff type file stream.
        :type stream: stream
        :keyword bool include_text_content: Include text lines and element references in the result.
        :keyword str content_type: Media type of the body sent to the API.
        :return: List[RecognizedForm]
        :rtype: list[~azure.ai.formrecognizer.RecognizedForm]
        :raises: ~azure.core.exceptions.HttpResponseError
        """
        if isinstance(stream, six.string_types):
            raise TypeError("Call begin_recognize_custom_forms_from_url() to analyze a document from a url.")

        include_text_content = kwargs.pop("include_text_content", False)
        content_type = kwargs.pop("content_type", None)
        if content_type is None:
            content_type = get_content_type(stream)

        return await self._client.analyze_with_custom_model(
            file_stream=stream,
            model_id=model_id,
            include_text_details=include_text_content,
            content_type=content_type,
            cls=kwargs.pop("cls", self._analyze_callback),
            polling=AsyncLROBasePolling(timeout=POLLING_INTERVAL, lro_algorithms=[AnalyzePolling()], **kwargs),
            **kwargs
        )

    @distributed_trace_async
    async def begin_recognize_custom_forms_from_url(
            self,
            model_id: str,
            url: str,
            **kwargs: Any
    ) -> List["RecognizedForm"]:
        """Analyze Form.

        :param str model_id: Model identifier.
        :param url: The url of the document.
        :type url: str
        :keyword bool include_text_content: Include text lines and element references in the result.
        :return: List[RecognizedForm]
        :rtype: list[~azure.ai.formrecognizer.RecognizedForm]
        :raises: ~azure.core.exceptions.HttpResponseError
        """
        if not isinstance(url, six.string_types):
            raise TypeError("Call begin_recognize_custom_forms() to analyze a document from a stream.")

        include_text_content = kwargs.pop("include_text_content", False)

        return await self._client.analyze_with_custom_model(
            file_stream={"source": url},
            model_id=model_id,
            include_text_details=include_text_content,
            cls=kwargs.pop("cls", self._analyze_callback),
            polling=AsyncLROBasePolling(timeout=POLLING_INTERVAL, lro_algorithms=[AnalyzePolling()], **kwargs),
            **kwargs
        )

    def get_form_training_client(self, **kwargs) -> FormTrainingClient:
        """Get an instance of a FormTrainingClient from FormRecognizerClient.

        :rtype: ~azure.ai.formrecognizer.FormTrainingClient
        :return: A FormTrainingClient
        """
        return FormTrainingClient(
            endpoint=self._endpoint,
            credential=self._credential,
            **kwargs
        )

    async def __aenter__(self) -> "FormRecognizerClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: "Any") -> None:
        await self._client.__aexit__(*args)

    async def close(self) -> None:
        """Close the :class:`~azure.ai.formrecognizer.FormRecognizerClient` session.
        """
        await self._client.__aexit__()