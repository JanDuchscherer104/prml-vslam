"""
Functionality for remote visualization over WebRTC.
"""
from __future__ import annotations
import typing
__all__: list[str] = ['call_http_api', 'disable_http_handshake', 'enable_webrtc', 'register_data_channel_message_callback']
def call_http_api(entry_point: str, query_string: str = '', data: str = '') -> str:
    """
    Emulates Open3D WebRTCWindowSystem's HTTP API calls. This is used when the HTTP handshake server is disabled (e.g. in Jupyter), and handshakes are done by this function.
    """
def disable_http_handshake() -> None:
    """
    Disables the HTTP handshake server. In Jupyter environment, WebRTC handshake is performed by call_http_api() with Jupyter's own COMMS interface, thus the HTTP server shall be turned off.
    """
def enable_webrtc() -> None:
    """
    Use WebRTC streams to display rendered gui window.
    """
def register_data_channel_message_callback(class_name: str, callback: typing.Callable[[str], str]) -> None:
    """
    Register callback for a data channel message.
    
    When the data channel receives a valid JSON string, the ``class_name`` property
    of the JSON object will be examined and the corresponding callback function will
    be called. The string return value of the callback will be sent back as a reply,
    if it is not empty.
    
    .. note:: Ordering between the message and the reply is not guaranteed, since
       some messages may take longer to process than others. If ordering is important,
       use a unique message id for every message and include it in the reply.
    
    .. code:: python
    
        # Register callback in Python
        import open3d as o3d
        o3d.visualization.webrtc_server.enable_webrtc()
        def send_ack(data):
            print(data)
            return "Received WebRTC data channel message with data: " + data
    
        o3d.visualization.webrtc_server.register_data_channel_message_callback(
            "webapp/input", send_ack)
    
    .. code:: js
    
        /* Send message in JavaScript to trigger callback. this is WebRTCStreamer object */
        this.dataChannel.send('{"class_name":"webapp/input", "data":"Test event"}')
    
    Args:
        class_name (str): The value of of the ``class_name`` property of the JSON object.
        callback (Callable[[str], str]): The callback function that will be called when a JSON object with the matching ``class_name`` is received via the data channel. The function should accept a ``string`` argument (corresponding to the event data, such as form data or updated value of a slider) and return a ``string``.
    
    Returns:
        None
    """
