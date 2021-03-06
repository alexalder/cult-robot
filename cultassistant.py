import json

from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2
from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2_grpc
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials

import assistant_helpers

from google.auth import app_engine
import googleapiclient.discovery


class CultTextAssistant(object):
    """Sample Assistant that supports text based conversations.
    Args:
      language_code: language for the conversation.
      device_model_id: identifier of the device model.
      device_id: identifier of the registered device instance.
      channel: authorized gRPC channel for connection to the
        Google Assistant API.
      deadline_sec: gRPC deadline in seconds for Google Assistant API call.
    """

    def __init__(self, secret, language_code="it-IT", device_model_id="cult-robot-telegram", device_id="cult-robot-telegram-app", deadline_sec=185):
        try:
            #credentials, project = google.auth.default(scopes=['https://www.googleapis.com/auth/assistant-sdk-prototype'])

            credentials = google.oauth2.credentials.Credentials(token=None, token_uri=secret.get('token_uri'), client_id=secret.get('client_id'), client_secret=secret.get('client_secret'), refresh_token=secret.get('refresh_token'))
            #credentials = google.oauth2.credentials.Credentials(token=None, token_uri=secret.get('token_uri'), client_id=secret.get('client_id'), client_secret=secret.get('client_secret'))
            http_request = google.auth.transport.requests.Request()
            #credentials.refresh(http_request)
            grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
                credentials, http_request, 'embeddedassistant.googleapis.com')
            self.device_model_id = device_model_id
            self.device_id = device_id
            self.conversation_state = None
            self.assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(
                grpc_channel,
            )
            self.deadline = deadline_sec
            self.language_code = language_code
            self.ready = True
        except Exception as e:
            self.ready = False
            print(e)

    def __enter__(self):
        return self

    def __exit__(self, etype, e, traceback):
        if e:
            return False

    def assist(self, text_query):
        """Send a text request to the Assistant and playback the response."""
        def iter_assist_requests():
            dialog_state_in = embedded_assistant_pb2.DialogStateIn(
                language_code=self.language_code,
                conversation_state=b''
            )
            if self.conversation_state:
                dialog_state_in.conversation_state = self.conversation_state
            config = embedded_assistant_pb2.AssistConfig(
                audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                    encoding='LINEAR16',
                    sample_rate_hertz=16000,
                    volume_percentage=0,
                ),
                dialog_state_in=dialog_state_in,
                device_config=embedded_assistant_pb2.DeviceConfig(
                    device_id=self.device_id,
                    device_model_id=self.device_model_id,
                ),
                text_query=text_query,
            )
            req = embedded_assistant_pb2.AssistRequest(config=config)
            assistant_helpers.log_assist_request_without_audio(req)
            yield req

        display_text = None
        for resp in self.assistant.Assist(iter_assist_requests(),
                                          self.deadline):
            assistant_helpers.log_assist_response_without_audio(resp)
            if resp.dialog_state_out.conversation_state:
                conversation_state = resp.dialog_state_out.conversation_state
                self.conversation_state = conversation_state
            if resp.dialog_state_out.supplemental_display_text:
                display_text = resp.dialog_state_out.supplemental_display_text
        return display_text
