// Turns a failed request into the words shown to the user.

import { ApiError } from "../services/api";

export interface ErrorDescription {
  title: string;
  message: string;
  /** False when repeating the same request cannot succeed (invalid input, missing record). */
  retryable: boolean;
}

export function describeError(error: unknown): ErrorDescription {
  const status = error instanceof ApiError ? error.status : -1;
  const message = error instanceof Error ? error.message : "Unexpected error.";

  switch (status) {
    // 502 and 504 come from a proxy in front of a backend that is down (the
    // Vite dev server, nginx): to the user that is the same as no connection.
    case 0:
    case 502:
    case 504:
      return {
        title: "Cannot reach the backend",
        message: "Start it from the backend folder with:\nuvicorn app.main:app --reload",
        retryable: true,
      };
    case 503:
      return { title: "The models are not loaded", message, retryable: true };
    case 422:
      return { title: "This input cannot be analysed", message, retryable: false };
    case 404:
      return { title: "Not found", message, retryable: false };
    default:
      return { title: "Something went wrong on the server", message, retryable: true };
  }
}
