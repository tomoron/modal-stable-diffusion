import os
import modal
import subprocess
from concurrent import futures

stub = modal.Stub("stable-diffusion-webui-download-output")

volume_key = 'stable-diffusion-webui-main'
volume = modal.SharedVolume().persist(volume_key)

webui_dir = "/content/stable-diffusion-webui/"
remote_outputs_dir = 'outputs'
output_dir = "./outputs"


@stub.function(
    shared_volumes={webui_dir: volume},
)
def list_output_image_path(cache: list[str]):
  absolute_remote_outputs_dir = os.path.join(webui_dir, remote_outputs_dir)
  image_path_list = []
  for root, dirs, files in os.walk(top=absolute_remote_outputs_dir):
    for file in files:
      if not file.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue

      absolutefilePath = os.path.join(root, file)
      relativeFilePath = absolutefilePath[(len(absolute_remote_outputs_dir)) :]
      if not relativeFilePath in cache:
        image_path_list.append(relativeFilePath.lstrip('/'))
  return image_path_list

def download_image_using_modal(image_path: str):
  download_dest = os.path.dirname(os.path.join(output_dir, image_path))
  os.makedirs(download_dest, exist_ok=True)
  subprocess.run(f'modal volume get {volume_key} {os.path.join(remote_outputs_dir, image_path)} {download_dest}', shell=True)

@stub.local_entrypoint()
def main():
  cache = []

  for root, dirs, files in os.walk(top=output_dir):
    for file in files:
      relativeFilePath = os.path.join(root, file)[len(output_dir) :]
      cache.append(relativeFilePath)

  image_path_list = list_output_image_path.call(cache)

  print(f'\n{len(image_path_list)}ファイルのダウンロードを行います\n')

  future_list = []
  with futures.ThreadPoolExecutor(max_workers=10) as executor:
    for image_path in image_path_list:
        future = executor.submit(download_image_using_modal, image_path=image_path)
        future_list.append(future)
    _ = futures.as_completed(fs=future_list)

  print(f'\nダウンロードが完了しました\n')
