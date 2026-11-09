import { IconPalette } from "../../icons";
import { THEMES, type ThemeName } from "../../theme/themes";
import { useTheme } from "../../theme/useTheme";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "../DropdownMenu/DropdownMenu";
import { IconButton } from "../IconButton/IconButton";

export function ThemePicker() {
  const { theme, setTheme } = useTheme();
  const current = THEMES.find((entry) => entry.name === theme);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <IconButton
          aria-label={`Colour theme: ${current?.label ?? theme}`}
          styleType="ghost"
          icon={<IconPalette />}
        />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup
          value={theme}
          onValueChange={(value) => setTheme(value as ThemeName)}
        >
          {THEMES.map((entry) => (
            <DropdownMenuRadioItem key={entry.name} value={entry.name}>
              {entry.label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
