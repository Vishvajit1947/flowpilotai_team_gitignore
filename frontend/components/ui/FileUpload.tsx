'use client';

import * as React from 'react';
import api from '@/lib/api';
import { Paperclip, X, Loader2 } from 'lucide-react';

export interface FileUploadProps {
  onUploadComplete: (url: string) => void;
  onRemove: () => void;
  disabled?: boolean;
}

const ACCEPTED_TYPES = ['application/pdf', 'image/png', 'image/jpeg'];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

export function FileUpload({ onUploadComplete, onRemove, disabled }: FileUploadProps) {
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [uploading, setUploading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);

    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError('Only PDF, PNG, and JPG files are allowed.');
      return;
    }
    if (file.size > MAX_SIZE) {
      setError('File must be under 10 MB.');
      return;
    }

    setSelectedFile(file);
    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await api.post<{ url: string }>('/inbox/upload-file', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60_000,
      });

      const url = res.data.url;
      onUploadComplete(url);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Upload failed.';
      setError(msg);
      setSelectedFile(null);
    } finally {
      setUploading(false);
    }
  };

  const handleRemove = () => {
    setSelectedFile(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = '';
    onRemove();
  };

  return (
    <div className="border border-dashed border-border p-4 rounded-lg bg-muted/20">
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        onChange={handleFileSelect}
        className="hidden"
        disabled={disabled || uploading}
        id="file-upload-input"
      />

      {selectedFile ? (
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            {uploading ? (
              <Loader2 className="h-4 w-4 animate-spin shrink-0 text-muted-foreground" />
            ) : (
              <Paperclip className="h-4 w-4 shrink-0 text-muted-foreground" />
            )}
            <span className="text-sm truncate">{selectedFile.name}</span>
            <span className="text-xs text-muted-foreground shrink-0">
              ({(selectedFile.size / 1024).toFixed(0)} KB)
            </span>
          </div>
          <button
            onClick={handleRemove}
            className="text-xs text-destructive hover:underline shrink-0 disabled:opacity-50"
            disabled={disabled || uploading}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <label
          htmlFor="file-upload-input"
          className="flex flex-col items-center gap-1 cursor-pointer"
        >
          <Paperclip className="h-5 w-5 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">
            Select a file (PDF, PNG, JPG) — max 10 MB
          </span>
        </label>
      )}

      {error && (
        <p className="text-xs text-destructive mt-2">{error}</p>
      )}
    </div>
  );
}
