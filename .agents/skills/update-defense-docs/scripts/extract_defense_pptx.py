#!/usr/bin/env python3
"""Extract ordered slide text and speaker notes from a PowerPoint deck."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}
NOTES_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"


def resolve_part(source: str, target: str) -> str:
    parts = list(PurePosixPath(source).parent.parts)
    for part in PurePosixPath(target).parts:
        if part == "..":
            parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)


def relationships(archive: ZipFile, source: str) -> dict[str, tuple[str, str]]:
    source_path = PurePosixPath(source)
    rel_path = source_path.parent / "_rels" / f"{source_path.name}.rels"
    try:
        root = ET.fromstring(archive.read(str(rel_path)))
    except KeyError:
        return {}
    return {
        rel.attrib["Id"]: (rel.attrib["Type"], resolve_part(source, rel.attrib["Target"]))
        for rel in root.findall("pr:Relationship", NS)
        if rel.attrib.get("TargetMode") != "External"
    }


def ordered_slide_parts(archive: ZipFile) -> list[str]:
    presentation = "ppt/presentation.xml"
    root = ET.fromstring(archive.read(presentation))
    rels = relationships(archive, presentation)
    parts = []
    for slide_id in root.findall("p:sldIdLst/p:sldId", NS):
        rel_id = slide_id.attrib[f"{{{NS['r']}}}id"]
        parts.append(rels[rel_id][1])
    return parts


def shape_paragraphs(shape: ET.Element) -> list[str]:
    paragraphs = []
    for paragraph in shape.findall(".//a:p", NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//a:t", NS)).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def extract_shapes(xml: bytes, notes: bool = False) -> list[dict[str, object]]:
    root = ET.fromstring(xml)
    extracted = []
    for shape in root.findall(".//p:sp", NS):
        placeholder = shape.find("p:nvSpPr/p:nvPr/p:ph", NS)
        placeholder_type = placeholder.attrib.get("type", "body") if placeholder is not None else None
        if notes and placeholder_type in {"sldImg", "sldNum", "hdr", "ftr", "dt"}:
            continue
        paragraphs = shape_paragraphs(shape)
        if not paragraphs:
            continue
        name_node = shape.find("p:nvSpPr/p:cNvPr", NS)
        extracted.append(
            {
                "name": name_node.attrib.get("name", "") if name_node is not None else "",
                "placeholder": placeholder_type,
                "paragraphs": paragraphs,
            }
        )
    return extracted


def extract_deck(path: Path) -> list[dict[str, object]]:
    with ZipFile(path) as archive:
        slides = []
        for number, slide_part in enumerate(ordered_slide_parts(archive), start=1):
            slide_shapes = extract_shapes(archive.read(slide_part))
            note_part = next(
                (target for rel_type, target in relationships(archive, slide_part).values() if rel_type == NOTES_REL),
                None,
            )
            note_shapes = extract_shapes(archive.read(note_part), notes=True) if note_part else []
            title_shape = next(
                (shape for shape in slide_shapes if shape["placeholder"] in {"title", "ctrTitle"}),
                None,
            )
            title = " ".join(title_shape["paragraphs"]) if title_shape else "Untitled visual slide"
            slides.append(
                {
                    "number": number,
                    "title": title,
                    "shapes": slide_shapes,
                    "notes": [p for shape in note_shapes for p in shape["paragraphs"]],
                }
            )
        return slides


def render_script(slides: list[dict[str, object]], deck: Path) -> str:
    lines = [
        "# Defense Speaker Script",
        "",
        f"> Source: `{deck.as_posix()}` speaker notes. Regenerate with `$update-defense-docs` after the deck changes.",
        "> Note text is preserved as written in PowerPoint; empty notes are stated explicitly.",
        "",
    ]
    for slide in slides:
        lines.extend([f"## Slide {slide['number']}: {slide['title']}", ""])
        notes = slide["notes"]
        if notes:
            for paragraph in notes:
                lines.extend([paragraph, ""])
        else:
            lines.extend(["_No speaker notes in the PowerPoint deck._", ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("deck", type=Path)
    parser.add_argument("--output", "-o", type=Path)
    parser.add_argument("--script-output", type=Path)
    args = parser.parse_args()
    data = extract_deck(args.deck)
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    if args.script_output:
        args.script_output.write_text(render_script(data, args.deck), encoding="utf-8")
    if not args.output and not args.script_output:
        print(payload)


if __name__ == "__main__":
    main()
