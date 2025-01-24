import os
import warnings
from concurrent.futures import ThreadPoolExecutor
from glob import glob

import gradio as gr
from modules.images import read_info_from_image, save_image_with_geninfo
from modules.paths_internal import default_output_dir
from modules.script_callbacks import on_ui_tabs
from PIL import Image


def _process(
    path: str,
    ext_from: str,
    ext_to: str,
    cpu: int,
    recursive: bool,
    delete: bool,
    force: bool,
):
    path = path.strip('"').strip()

    if os.path.isfile(path):
        if path.endswith(ext_from):
            files = [os.path.normpath(path)]
        else:
            gr.Warning(f'File "{path}" is not .{ext_from}')
            return

    elif os.path.isdir(path):
        if recursive:
            files = glob(os.path.join(path, "**", f"*.{ext_from}"), recursive=True)
        else:
            files = [
                os.path.join(path, f) for f in os.listdir(path) if f.endswith(ext_from)
            ]

        if len(files) == 0:
            gr.Warning(f'No ".{ext_from}" image was found in folder "{path}"')
            return

    else:
        gr.Warning(f'Path "{path}" does not exist')
        return

    gr.Info(f"Processing {len(files)} files, please hold...")

    def _process(path: str):
        try:
            img = Image.open(path)
        except Image.DecompressionBombError:
            print(f'Skipping "{path}" due to DecompressionBombError...')
            return

        info, _ = read_info_from_image(img)

        if info is None or not info:
            if not force:
                return

        save_image_with_geninfo(img, info, path.replace(ext_from, ext_to))

        if delete:
            os.remove(path)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        with ThreadPoolExecutor(max_workers=max(1, int(cpu))) as executor:
            for file in files:
                executor.submit(_process, file)

    gr.Info("Done!")


def RewriteHistory():
    with gr.Blocks() as REEE:
        with gr.Row():
            path = gr.Textbox(
                value=None,
                label="Path to Folder / File",
                info="absolute path is recommended",
                placeholder=os.path.abspath(default_output_dir),
                max_lines=1,
                lines=1,
                scale=5,
            )
            btn = gr.Button(
                value="Process",
                variant="primary",
                scale=1,
            )
        with gr.Row():
            ext_from = gr.Dropdown(
                value="png",
                label="Target Extension",
                info="from",
                choices=("png", "jpg", "jpeg", "webp", "avif"),
                scale=2,
            )
            ext_to = gr.Dropdown(
                value="jpg",
                label="Result Extension",
                info="to",
                choices=("png", "jpg", "jpeg", "webp", "avif"),
                scale=2,
            )
            cpu = gr.Number(
                value=4,
                step=1,
                label="Concurrency",
                info="processes in parallel",
                scale=1,
            )
            with gr.Column(scale=1):
                recursive = gr.Checkbox(
                    value=True,
                    label="Recursive",
                )
                delete = gr.Checkbox(
                    value=True,
                    label="Delete old files that have been converted",
                )
                force = gr.Checkbox(
                    value=True,
                    label="Convert files even if it does not contain infotext",
                )

        inputs = [path, ext_from, ext_to, cpu, recursive, delete, force]
        for comp in inputs:
            comp.do_not_save_to_config = True

        btn.do_not_save_to_config = True
        btn.click(fn=_process, inputs=inputs)

    return [(REEE, "Rewrite History", "sd-webui-rewrite-history")]


on_ui_tabs(RewriteHistory)
