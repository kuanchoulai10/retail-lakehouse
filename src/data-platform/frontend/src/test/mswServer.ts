import { setupServer } from "msw/node";

// One MSW server for every test file: tests add handlers with server.use, and setup.ts resets them after each test.
export const server = setupServer();
