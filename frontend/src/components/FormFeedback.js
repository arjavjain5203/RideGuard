export function FieldError({ id, message }) {
  if (!message) {
    return null;
  }

  return (
    <p id={id} role="alert" className="mt-2 text-sm font-medium text-red-600">
      {message}
    </p>
  );
}

export function SectionError({ message, className = "" }) {
  if (!message) {
    return null;
  }

  return (
    <div
      role="alert"
      className={`rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 ${className}`}
    >
      {message}
    </div>
  );
}
