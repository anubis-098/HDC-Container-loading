import { useEffect, useRef, useState } from "react";

export function ProvinceField({
  value,
  onChange,
  provinces,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  provinces: { name: string }[];
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const input = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const query = value.trim();
  const matches =
    query.length < 2
      ? []
      : provinces
          .filter((p) => p.name.includes(query))
          .sort(
            (a, b) =>
              Number(b.name.startsWith(query)) -
                Number(a.name.startsWith(query)) ||
              a.name.localeCompare(b.name, "th"),
          );
  const visible = open && query.length >= 2 && !disabled;
  useEffect(() => {
    input.current?.setCustomValidity(
      value.trim() && !provinces.some((p) => p.name === value.trim())
        ? "กรุณาเลือกจังหวัดจากรายการแนะนำ"
        : "",
    );
  }, [value, provinces]);
  useEffect(() => {
    list.current?.children[active]?.scrollIntoView({ block: "nearest" });
  }, [active]);
  function select(name: string) {
    onChange(name);
    setOpen(false);
    setActive(-1);
  }
  return (
    <div
      className="province-field"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <label htmlFor="truck-province">จังหวัดป้ายทะเบียน</label>
      <input
        ref={input}
        id="truck-province"
        role="combobox"
        maxLength={60}
        value={value}
        disabled={disabled}
        autoComplete="off"
        placeholder="ไม่บังคับกรอก"
        aria-autocomplete="list"
        aria-expanded={visible}
        aria-controls="province-options"
        aria-describedby="province-hint"
        aria-activedescendant={
          visible && active >= 0 && matches[active]
            ? `province-option-${active}`
            : undefined
        }
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          onChange(event.target.value);
          setActive(-1);
          setOpen(true);
        }}
        onKeyDown={(event) => {
          if (event.nativeEvent.isComposing) return;
          if (event.key === "Escape") {
            event.preventDefault();
            setOpen(false);
          }
          if (
            (event.key === "ArrowDown" || event.key === "ArrowUp") &&
            matches.length
          ) {
            event.preventDefault();
            setOpen(true);
            setActive((index) =>
              event.key === "ArrowDown"
                ? Math.min(index + 1, matches.length - 1)
                : Math.max(0, index - 1),
            );
          }
          if (event.key === "Enter" && visible) {
            event.preventDefault();
            if (matches[active >= 0 ? active : 0])
              select(matches[active >= 0 ? active : 0].name);
          }
        }}
      />
      <small id="province-hint">พิมพ์ 2 ตัวอักษร แล้วเลือกจังหวัด</small>
      {visible && (
        <div className="province-dropdown">
          <ul
            id="province-options"
            role="listbox"
            aria-label="จังหวัดป้ายทะเบียน"
            ref={list}
          >
            {matches.map((province, index) => (
              <li
                key={province.name}
                id={`province-option-${index}`}
                role="option"
                aria-selected={active === index}
                onMouseDown={(event) => event.preventDefault()}
                onMouseEnter={() => setActive(index)}
                onClick={() => select(province.name)}
              >
                {province.name}
              </li>
            ))}
          </ul>
          <small role="status">
            {matches.length
              ? `พบ ${matches.length} จังหวัด`
              : "ไม่พบจังหวัด กรุณาตรวจสอบคำค้น"}
          </small>
        </div>
      )}
    </div>
  );
}
