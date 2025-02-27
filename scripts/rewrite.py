import os
import warnings
from concurrent.futures import ThreadPoolExecutor
from glob import glob

import gradio as gr
from modules.images import read_info_from_image, save_image_with_geninfo
from modules.paths_internal import default_output_dir
from modules.script_callbacks import on_ui_tabs
from PIL import Image


def __process(
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


def __process_single(path_from: str, path_to: str):
    path_from = path_from.strip('"').strip()
    path_to = path_to.strip('"').strip()

    if not os.path.isfile(path_from):
        gr.Warning(f'File "{path_from}" does not exist')
        return

    if not os.path.isfile(path_to):
        gr.Warning(f'File "{path_to}" does not exist')
        return

    try:
        img_from = Image.open(path_from)
        img_to = Image.open(path_to)
    except Image.DecompressionBombError:
        gr.Warning("Skipping due to DecompressionBombError...")
        return
    except Image.UnidentifiedImageError:
        gr.Warning("Failed to read Image...")
        return

    info, _ = read_info_from_image(img_from)

    if info is None or not info:
        gr.Warning("No Infotext Detected...")
        return

    save_image_with_geninfo(img_to, info, path_to)

    gr.Info("Done!")


def RewriteHistory():
    with gr.Blocks() as REEE:
        group_a = gr.Group(elem_classes="rewrite-group")
        group_a.__enter__()

        with gr.Row():
            path = gr.Textbox(
                value=None,
                label="Path to Folder / File",
                info="absolute path is recommended",
                placeholder=os.path.abspath(default_output_dir),
                max_lines=1,
                lines=1,
                scale=8,
            )
            btn = gr.Button(
                value="Process",
                variant="primary",
                scale=1,
            )
        with gr.Row():
            ext_from = gr.Dropdown(
                value="png",
                label="Source Extension",
                info="from",
                choices=("png", "jpg", "jpeg", "webp", "avif"),
                scale=3,
            )
            ext_to = gr.Dropdown(
                value="jpg",
                label="Target Extension",
                info="to",
                choices=("png", "jpg", "jpeg", "webp", "avif"),
                scale=3,
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

        group_a.__exit__()
        group_b = gr.Group(elem_classes="rewrite-group")
        group_b.__enter__()

        with gr.Row():
            path_from = gr.Textbox(
                value=None,
                label="Source Image",
                info="absolute path is recommended",
                placeholder="C://foo/bar.png",
                max_lines=1,
                lines=1,
                scale=4,
            )
            path_to = gr.Textbox(
                value=None,
                label="Target Image",
                info="absolute path is recommended",
                placeholder="C://bar/foo.jpg",
                max_lines=1,
                lines=1,
                scale=4,
            )
            btn_single = gr.Button(
                value="Transfer",
                variant="primary",
                scale=1,
            )

        group_b.__exit__()

        inputs = [path, ext_from, ext_to, cpu, recursive, delete, force]
        for comp in inputs:
            comp.do_not_save_to_config = True

        btn.do_not_save_to_config = True
        btn.click(fn=__process, inputs=inputs)

        for comp in (group_a, group_b, path_from, path_to, btn_single):
            comp.do_not_save_to_config = True

        btn_single.click(fn=__process_single, inputs=[path_from, path_to])

    return [(REEE, "Rewrite History", "sd-webui-rewrite-history")]


on_ui_tabs(RewriteHistory)
