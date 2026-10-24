const BASE = "/api/repairclaim/v1";
let csrf = "";
export function setCsrf(value: string) {
  csrf = value;
}
export class ApiError extends Error {
  status: number;
  constructor(code: string, status: number) {
    super(code.replaceAll("_", " "));
    this.status = status;
  }
}
export async function api(
  path: string,
  body?: unknown,
  method = body === undefined ? "GET" : "POST",
): Promise<any> {
  const response = await fetch(BASE + path, {
    method,
    credentials: "same-origin",
    headers: {
      ...(body !== undefined ? { "content-type": "application/json" } : {}),
      ...(method !== "GET" ? { "x-csrf-token": csrf } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response
      .json()
      .catch(() => ({ code: "request_failed" }));
    throw new ApiError(data.code, response.status);
  }
  return response.status === 204 ? null : response.json();
}
export async function upload(path: string, file: File) {
  const response = await fetch(BASE + path, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "content-type": "application/octet-stream",
      "x-csrf-token": csrf,
    },
    body: file,
  });
  if (!response.ok)
    throw new ApiError((await response.json()).code, response.status);
  return response.json();
}
export async function download(path: string, name: string) {
  const approvedAction =
    path.startsWith("/packets/") && path.endsWith("/download");
  const response = await fetch(BASE + path, {
    credentials: "same-origin",
    method: approvedAction ? "POST" : "GET",
    ...(approvedAction
      ? {
          headers: { "x-csrf-token": csrf, "content-type": "application/json" },
          body: "{}",
        }
      : {}),
  });
  if (!response.ok)
    throw new ApiError((await response.json()).code, response.status);
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const image = (path: string) => BASE + path;
