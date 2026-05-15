interface TabItem<T extends string> {
  id: T;
  label: string;
}

interface TabNavProps<T extends string> {
  tabs: ReadonlyArray<TabItem<T>>;
  active: T;
  onChange: (id: T) => void;
  /** Numera las pestañas con índice tipo lámina (01 / 02). */
  numbered?: boolean;
}

export function TabNav<T extends string>({
  tabs,
  active,
  onChange,
  numbered = true,
}: TabNavProps<T>) {
  return (
    <div className="atlas-tabs" role="tablist">
      {tabs.map((tab, i) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          className="atlas-tab"
          onClick={() => onChange(tab.id)}
        >
          {numbered && (
            <span className="atlas-tab__idx">
              {String(i + 1).padStart(2, '0')}
            </span>
          )}
          {tab.label}
        </button>
      ))}
    </div>
  );
}
