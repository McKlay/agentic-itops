import { useState, useEffect, useCallback } from 'react';

interface SearchInputProps {
  placeholder?: string;
  onSearch: (query: string) => void;
  value?: string;
}

export default function SearchInput({ placeholder = 'Search...', onSearch, value: externalValue }: SearchInputProps) {
  const [value, setValue] = useState(externalValue || '');

  useEffect(() => {
    if (externalValue !== undefined) setValue(externalValue);
  }, [externalValue]);

  const debounce = useCallback(() => {
    const timer = setTimeout(() => onSearch(value), 250);
    return () => clearTimeout(timer);
  }, [value, onSearch]);

  useEffect(() => debounce(), [debounce]);

  return (
    <input
      type="text"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      placeholder={placeholder}
      className="w-full max-w-sm px-4 py-2 rounded-xl border border-[var(--line)] bg-[var(--surface)] text-sm text-[var(--text)] placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--purple)] focus:ring-2 focus:ring-[var(--purple-soft)] transition-all duration-[var(--transition-fast)]"
    />
  );
}
