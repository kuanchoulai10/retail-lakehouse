// Translates the catalog API's column type text (see the backend table dto.py docstring) into
// a Spark SQL type. `required` is the API's own syntax: on a struct field it becomes
// NOT NULL; on a list element or map value it is dropped, since Spark DDL cannot say it there.
// A primitive Spark has no name for (time, variant, ...) is passed through upper-cased.

const PRIMITIVES: Record<string, string> = {
  boolean: "BOOLEAN",
  int: "INT",
  long: "BIGINT",
  float: "FLOAT",
  double: "DOUBLE",
  date: "DATE",
  timestamp: "TIMESTAMP_NTZ",
  timestamp_ns: "TIMESTAMP_NTZ",
  timestamptz: "TIMESTAMP",
  timestamptz_ns: "TIMESTAMP",
  string: "STRING",
  uuid: "STRING",
  binary: "BINARY",
};

export function quoteIdentifier(name: string): string {
  return `\`${name.replaceAll("`", "``")}\``;
}

class TypeText {
  private position = 0;

  constructor(private readonly text: string) {}

  type(): string {
    this.skipSpaces();
    if (this.consume("struct<")) return this.struct();
    if (this.consume("list<")) {
      this.optionalRequired();
      const element = this.type();
      this.expect(">");
      return `ARRAY<${element}>`;
    }
    if (this.consume("map<")) {
      const key = this.type();
      this.expect(",");
      this.optionalRequired();
      const value = this.type();
      this.expect(">");
      return `MAP<${key}, ${value}>`;
    }
    return this.primitive();
  }

  end(): void {
    this.skipSpaces();
    if (this.position !== this.text.length) this.fail();
  }

  private struct(): string {
    const fields: string[] = [];
    this.skipSpaces();
    while (!this.consume(">")) {
      if (fields.length > 0) this.expect(",");
      this.skipSpaces();
      const colon = this.text.indexOf(":", this.position);
      if (colon < 0) this.fail();
      const name = this.text.slice(this.position, colon).trim();
      this.position = colon + 1;
      const required = this.optionalRequired();
      const type = this.type();
      fields.push(`${quoteIdentifier(name)}: ${type}${required ? " NOT NULL" : ""}`);
      this.skipSpaces();
    }
    return `STRUCT<${fields.join(", ")}>`;
  }

  private primitive(): string {
    const match = /^[a-z_0-9]+(\([^)]*\)|\[[^\]]*\])?/.exec(this.text.slice(this.position));
    if (match === null) this.fail();
    this.position += match[0].length;
    const name = match[0];
    if (name.startsWith("decimal")) return name.toUpperCase().replaceAll(" ", "");
    if (name.startsWith("fixed")) return "BINARY";
    return PRIMITIVES[name] ?? name.toUpperCase();
  }

  private optionalRequired(): boolean {
    this.skipSpaces();
    return this.consume("required ");
  }

  private consume(token: string): boolean {
    if (!this.text.startsWith(token, this.position)) return false;
    this.position += token.length;
    return true;
  }

  private expect(token: string): void {
    this.skipSpaces();
    if (!this.consume(token)) this.fail();
  }

  private skipSpaces(): void {
    while (this.text[this.position] === " ") this.position += 1;
  }

  private fail(): never {
    throw new Error(`cannot read column type "${this.text}" at ${this.position}`);
  }
}

export function sparkColumnType(text: string): string {
  const reader = new TypeText(text);
  const type = reader.type();
  reader.end();
  return type;
}
