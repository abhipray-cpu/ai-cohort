"""Private restricted-process protocol; do not expose this command through the web."""

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    # Container cgroups are the outer fence; native macOS also gets process limits.
    if sys.platform != "win32":
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (45, 45))
        resource.setrlimit(resource.RLIMIT_FSIZE, (40 * 1024 * 1024, 40 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    from repairclaim_api.documents import _open, parse_document, sanitized_attachment
    from repairclaim_api.errors import DomainError

    try:
        request = json.loads(sys.stdin.buffer.read(29 * 1024 * 1024))
        data = base64.b64decode(request["data"], validate=True)
        operation, filename = request["operation"], request["filename"]
        if operation == "parse":
            result = parse_document(data, filename)
        elif operation == "sanitize":
            result = sanitized_attachment(data, filename, request.get("redactions", []))
        elif operation == "preview":
            import pymupdf

            with _open(data, filename) as document:
                number = request.get("page", 1)
                if type(number) is not int or not 1 <= number <= len(document):
                    raise DomainError("invalid_page", 422)
                page = document[number - 1]
                scale = min(1.5, 1200 / max(page.rect.width, page.rect.height))
                result = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes(
                    "png"
                )
        else:
            raise DomainError("invalid_parser_operation", 422)
        if isinstance(result, bytes):
            result = {"bytes": base64.b64encode(result).decode("ascii")}
        sys.stdout.write(json.dumps({"ok": result}))
    except DomainError as error:
        sys.stdout.write(json.dumps({"error": error.code}))
    except BaseException:  # noqa: BLE001 — restricted protocol must not disclose parser internals
        sys.stdout.write(json.dumps({"error": "parser_failed"}))


if __name__ == "__main__":
    main()
