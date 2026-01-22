# code-smells specs

## overview

As a senior software engineer that works at a very fast pace, writing small to big projects based on several different technologies. I am a heavy user of many actual coding tools like Cursor, Claude Code and GitHub Copilot.  

I am building a mechanism to keep sets of instructions and configurations to guide the coding agents and also to serve as guidelines and checklists for code reviews of projects that third-party contractors develop for me. As I work alone and for an enterprise company.

The settings can be global and project specific. Some rules applies in general, but most are targeted to specific technologies or frameworks. Also, there are environment specific settings and requirements for the runtime environment.

I want to standardize the coding rules - for guidance and reviews - across my different projects. I want to feel safe about the rules being effectively applied to all projects. 

Setting up this mechanism must be easy and error prone.

## architecture

### high level overview

### components

#### *rules repository* (commands/skills/you name it)

- define rules: coding standards, guidelines, blueprints, review check lists, ...
- rules may be global or workspace specific (project) 

#### VSIX IDE Extension


#### Custom code review agents


#### GitHub Actions (CI workflows)
