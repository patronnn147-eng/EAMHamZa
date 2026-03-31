import { buildPrompt } from "./buildPrompt.js";

const prompt = buildPrompt({
  skill: "coding",
  sop: "feature-build",
  gsd: true,
  extra: `
Build a JWT authentication system using Node.js and Express.
`
});

console.log(prompt);