// A snake_case key as a sentence-case label: "rewrite_data_files" reads "Rewrite data files".
export function sentenceCase(key: string): string {
  const words = key.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
