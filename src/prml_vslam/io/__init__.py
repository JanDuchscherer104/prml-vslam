"""Input and output helpers for videos, logs, and benchmark artifacts."""

from prml_vslam.interfaces import CameraIntrinsics, FramePacket, SE3Pose

from .cv2_producer import (
    Cv2FrameProducer,
    Cv2ProducerConfig,
    Cv2ReplayMode,
    open_cv2_replay_stream,
)
from .record3d import (
    Record3DDevice,
    Record3DDeviceType,
    Record3DFrame,
    Record3DStreamConfig,
    Record3DStreamSession,
    Record3DStreamSnapshot,
    Record3DStreamState,
    Record3DTransportId,
    Record3DUSBPacketStream,
    Record3DUSBPacketStreamConfig,
    record3d_frame_to_packet,
)
from .wifi_packets import Record3DWiFiMetadata, decode_record3d_wifi_depth
from .wifi_session import Record3DWiFiStreamConfig, Record3DWiFiStreamSession
from .wifi_signaling import Record3DWiFiSignalingClient, normalize_record3d_device_address

__all__ = [
    "CameraIntrinsics",
    "Cv2FrameProducer",
    "Cv2ProducerConfig",
    "Cv2ReplayMode",
    "FramePacket",
    "Record3DDevice",
    "Record3DDeviceType",
    "Record3DFrame",
    "Record3DStreamConfig",
    "Record3DStreamSession",
    "Record3DStreamSnapshot",
    "Record3DStreamState",
    "Record3DTransportId",
    "Record3DUSBPacketStream",
    "Record3DUSBPacketStreamConfig",
    "Record3DWiFiMetadata",
    "Record3DWiFiSignalingClient",
    "Record3DWiFiStreamConfig",
    "Record3DWiFiStreamSession",
    "SE3Pose",
    "decode_record3d_wifi_depth",
    "normalize_record3d_device_address",
    "open_cv2_replay_stream",
    "record3d_frame_to_packet",
]
