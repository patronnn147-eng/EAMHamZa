import fs from "fs";
import path from "path";

const read = (filePath) =>
  fs.readFileSync(path.resolve(filePath), "utf-8");

export function buildPrompt({
  skill,
  sop,
  gsd = false,
  extra = ""
}) {
  const global = read("../CLAUDE.md");

  const core = `
${read("../core/identity.md")}
${read("../core/workflow.md")}
${read("../core/engineering.md")}
${read("../core/communication.md")}
`;

  const skillContent = skill ? read(`../skills/${skill}.md`) : "";
  const sopContent = sop ? read(`../sops/${sop}.md`) : "";
  const gsdContent = gsd ? read("../gsd/execution.md") : "";

  return `
########## GLOBAL ##########
${global}

########## CORE ##########
${core}

########## MODE ##########
${gsdContent}

########## SKILL ##########
${skillContent}

########## SOP ##########
${sopContent}

########## TASK ##########
${extra}
`;
}