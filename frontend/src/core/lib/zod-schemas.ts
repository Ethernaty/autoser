export type SchemaValidator<T> = (input: unknown) => input is T;

export function assertSchema<T>(input: unknown, validator: SchemaValidator<T>, message: string): T {
  if (!validator(input)) {
    throw new Error(message);
  }
  return input;
}
