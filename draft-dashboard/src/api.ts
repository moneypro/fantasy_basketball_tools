export async function api<T>(
  path: string,
  method = "GET",
  options: { signal?: AbortSignal; timeoutMs?: number } = {},
): Promise<T> {
  const timeout = AbortSignal.timeout(
    options.timeoutMs ??
      (path === "/api/bootstrap"
        ? 60_000
        : path === "/api/refresh"
          ? 45_000
          : path === "/api/draft"
            ? 8000
            : 15_000),
  );
  try {
    const response = await fetch(path, {
      method,
      signal: options.signal
        ? AbortSignal.any([options.signal, timeout])
        : timeout,
    });
    const body = await response.json();
    if (!response.ok)
      throw new Error(
        body.error ?? "The local server could not complete this request.",
      );
    return body;
  } catch (error) {
    if (timeout.aborted)
      throw new Error(
        "The connection is too slow. Saved data is kept; try again when the connection improves.",
      );
    if (error instanceof TypeError)
      throw new Error(
        "The server could not be reached. Check your connection and try again.",
      );
    throw error;
  }
}
