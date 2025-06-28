const themes = ["family_guy", "rick_and_morty"] as const;
type Theme = (typeof themes)[number];

export default function ThemeToggle({
  value,
  onChange,
  darkMode = false,
}: {
  value: Theme;
  onChange: (t: Theme) => void;
  darkMode?: boolean;
}) {
  const formatThemeName = (theme: string) => {
    if (theme === "family_guy") return "Family Guy";
    if (theme === "rick_and_morty") return "Rick And Morty";
    return theme.replace("_", " ").replace(/\b\w/g, l => l.toUpperCase());
  };

  const getThemeImage = (theme: string) => {
    if (theme === "family_guy") return "/family_guy.jpeg";
    if (theme === "rick_and_morty") return "/rick_and_morty.jpeg";
    return "";
  };

  return (
    <div className="flex gap-4">
      {themes.map(t => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`relative px-6 py-4 rounded-xl transition-all overflow-hidden group ${
            value === t 
              ? "ring-4 ring-blue-500 shadow-lg scale-105" 
              : "hover:scale-102 hover:shadow-md"
          }`}
          style={{
            backgroundImage: `url(${getThemeImage(t)})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            minWidth: '120px',
            minHeight: '80px'
          }}
        >
          {/* Overlay */}
          <div className={`absolute inset-0 ${
            value === t 
              ? "bg-blue-600/30" 
              : darkMode
                ? "bg-gray-900/70 group-hover:bg-gray-900/60"
                : "bg-black/50 group-hover:bg-black/40"
          } transition-colors`} />
          
          {/* Text */}
          <span className="relative z-10 text-white font-bold text-sm drop-shadow-lg">
            {formatThemeName(t)}
          </span>
        </button>
      ))}
    </div>
  );
}
