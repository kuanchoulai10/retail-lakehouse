# 8. The design system builds on Serendie tokens, not on Serendie's React library

Date: 2026-11-08

Status: Accepted

## Context

The console's UI was a set of shadcn primitives styled page by page, with a monochrome look and a dark mode. The owner wants front-end work to be systematic and to scale: one design system, owned in this repo, that every page is built from. Two longer goals shape it. The whole console will be operable from the keyboard, and users will pick among colour themes.

The owner chose the visual language of Serendie, Mitsubishi Electric's open-source design system (MIT), for its Japanese traditional colour themes. Serendie ships design tokens (`@serendie/design-token`), symbols (`@serendie/symbols`) and a React library (`@serendie/ui`, on Ark UI and Panda CSS).

## Considered options

1. Keep the shadcn layer and restyle it page by page.
2. Adopt `@serendie/ui`.
3. Use Serendie's tokens and symbols, treat its component docs as the design spec, and build the components ourselves on Radix and Tailwind 4.

## Decision

Option 3. The design system lives in `src/design-system` as an npm workspace package, `@retail-lakehouse/design-system`, consumed as TypeScript source.

- **Three token layers.** Serendie tokens (`--sd-*`) feed design-system semantic tokens (`--ds-*`), which Tailwind exposes as utilities. Only the design system reads `--sd-*`.
- **Three themes**, KONJO (default), ASAGI and KURIKAWA, switched with Serendie's `data-panda-theme` attribute. Light values only, no dark mode, no colour derived by us.
- **Components on Radix and Tailwind 4**, named as Serendie names them where Serendie has the component. Serendie's docs are the spec for sizes, states and spacing.
- **Two window classes** split at 768px, following Serendie: compact (touch sizes, 44px targets) and expanded (dense, 36px controls and rows), so the console works on phones and desktops.
- **Quality gates.** Storybook is the catalogue, with axe checks and keyboard play functions run as tests. A unit test computes WCAG contrast for every theme. A console test, `designSystemBoundary.test.ts`, keeps console code free of raw colours, `--sd-*`, direct Radix or icon-package imports, and deep design-system paths.
- **Not adopted:** `@serendie/ui`, Ark UI, Panda CSS.

## Consequences

- One headless stack (Radix) and one styling engine (Tailwind) stay in the dependency tree.
- We own every component and its accessibility. `@serendie/ui` has no command palette or combobox, which the keyboard goal needs, so we would have built them anyway.
- We follow Serendie's docs by hand. A Serendie change does not reach us until we copy it.
- Ported Serendie values or source carry the MIT notice, and the README credits Serendie. The product UI shows no Serendie or Mitsubishi Electric name.
- The dark mode is gone. If it returns, a `konjo-dark` theme is the way in, because themes already switch by attribute.
- The console image build now needs `src/design-system` in its context, and a design-system change rebuilds the console image.
