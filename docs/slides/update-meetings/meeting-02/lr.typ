#let done_table_row = (
  [LR],
  [ViSTA-SLAM integration],
)
#let challenges_table_row = (
  [LR],
  [CUDA version mismatch],
)
#let next_steps_table_row = (
  [LR],
  [CUDA 13.0 toolkit, streaming validation],
)

#let done_detail_body = [
  == Done
  - Integrated ViSTA-SLAM as submodule with offline + streaming backend
  - CLI `run` command and Streamlit pipeline page wired to real backend
  - Built DBoW3Py C extension for loop detection
]

#let challenges_detail_body = [
  == Challenges
  - Driver (CUDA 13.0) vs toolkit (12.6) vs torch version alignment
  - GPU hardware fault required system reboot
]

#let next_steps_detail_body = [
  == Next Steps
  - Install CUDA 13.0 toolkit, rebuild RoPE2D extension
  - End-to-end streaming test on ADVIO sequences
]
