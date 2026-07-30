class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, data: unknown) {
    super(`API Error: ${status}`);
    this.status = status;
    this.data = data;
  }
}

async function getAuthToken(): Promise<string | null> {
  try {
    const res = await fetch('/.auth/me');
    const data = await res.json();
    return data?.clientPrincipal?.identityProvider ? data.clientPrincipal.userId : null;
  } catch {
    return null;
  }
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await getAuthToken();
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let data: unknown;
    try {
      data = await response.json();
    } catch {
      data = { message: response.statusText };
    }
    throw new ApiError(response.status, data);
  }

  return response.json() as Promise<T>;
}
