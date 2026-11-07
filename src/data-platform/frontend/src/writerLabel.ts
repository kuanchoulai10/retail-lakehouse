const WRITER_LABELS: Record<string, string> = {
  kafka_connect: "Kafka Connect",
  spark: "Spark",
  unknown: "Unknown",
};

export function writerLabel(writer: string): string {
  return WRITER_LABELS[writer] ?? writer;
}
