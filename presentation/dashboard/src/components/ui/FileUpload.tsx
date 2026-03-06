export function FileUpload({ onUpload }: { onUpload: (file: File) => void }) {
  return <div className="rounded-lg border-2 border-dashed border-gray-300 p-6 text-center"><p className="text-sm text-gray-500">Drag & drop or click to browse</p><input type="file" className="mt-2" onChange={(e) => { if (e.target.files?.[0]) onUpload(e.target.files[0]); }} /></div>;
}
