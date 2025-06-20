const themes = ["family_guy", "rick_and_morty"] as const;
type Theme = (typeof themes)[number];

export default function ThemeToggle({
  value,
  onChange,
}: {
  value: Theme;
  onChange: (t: Theme) => void;
}) {
  const formatThemeName = (theme: string) => {
    if (theme === "family_guy") return "Family Guy";
    if (theme === "rick_and_morty") return "Rick And Morty";
    return theme.replace("_", " ").replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className="flex gap-4">
      {themes.map(t => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`px-4 py-2 rounded transition-colors
            ${value === t 
              ? "bg-blue-600 text-white shadow-md" 
              : "bg-gray-200 hover:bg-gray-300 text-gray-700"
            }`}>
          {formatThemeName(t)}
        </button>
      ))}
    </div>
  );
}
