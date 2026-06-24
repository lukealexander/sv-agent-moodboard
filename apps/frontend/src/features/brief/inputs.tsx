/** The four answer inputs: free text, agent chips, reference drop, palette picker. */

import {
  useEffect,
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type KeyboardEvent,
} from "react";
import { clamp, uid } from "./helpers";
import { CheckIcon, CloseIcon, ImagesIcon, PlusIcon } from "./icons";
import { PALETTE_AXES, SWATCHES } from "./stages";
import type { AnswerValue, PaletteValue, ReferenceImage } from "./types";
import styles from "./inputs.module.css";

interface BaseProps {
  onChange: (value: AnswerValue) => void;
  labelledBy?: string;
  autoFocus?: boolean;
}

const TEXT_SOFT_MAX = 400;
const MAX_IMAGE_BYTES = 8 * 1024 * 1024;

/* ---- Free text ---- */

export function TextAnswer({
  value,
  onChange,
  labelledBy,
  autoFocus,
  placeholder,
}: BaseProps & { value: string; placeholder?: string }) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  const remaining = TEXT_SOFT_MAX - value.length;
  return (
    <div className={styles.textWrap}>
      <textarea
        ref={ref}
        className={styles.textarea}
        value={value}
        rows={2}
        autoFocus={autoFocus}
        aria-labelledby={labelledBy}
        maxLength={TEXT_SOFT_MAX}
        placeholder={placeholder}
        onChange={(e) => onChange({ kind: "text", text: e.target.value })}
      />
      {remaining <= 80 && (
        <span className={styles.counter} aria-live="polite">
          {remaining} left
        </span>
      )}
    </div>
  );
}

/* ---- Agent-proposed chips ---- */

export function ChipChoice({
  value,
  seedChips,
  onChange,
  labelledBy,
}: BaseProps & { value: string[]; seedChips: string[] }) {
  const [draft, setDraft] = useState("");
  // Show seeds plus anything the user typed in, in a stable order.
  const available = [...seedChips, ...value.filter((c) => !seedChips.includes(c))];

  const toggle = (chip: string) => {
    const next = value.includes(chip)
      ? value.filter((c) => c !== chip)
      : [...value, chip];
    onChange({ kind: "chips", chips: next });
  };

  const addDraft = () => {
    const c = draft.trim();
    if (!c || value.includes(c)) {
      setDraft("");
      return;
    }
    onChange({ kind: "chips", chips: [...value, c] });
    setDraft("");
  };

  const onDraftKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addDraft();
    }
  };

  return (
    <div className={styles.chips} role="group" aria-labelledby={labelledBy}>
      {available.map((chip) => {
        const selected = value.includes(chip);
        return (
          <button
            key={chip}
            type="button"
            className={styles.chip}
            data-selected={selected}
            aria-pressed={selected}
            onClick={() => toggle(chip)}
          >
            {selected && <CheckIcon className={styles.chipCheck} width={15} height={15} />}
            {chip}
          </button>
        );
      })}
      <div className={styles.chipAdd}>
        <input
          className={styles.chipAddInput}
          value={draft}
          placeholder="Add your own"
          aria-label="Add your own mood"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onDraftKey}
          onBlur={addDraft}
        />
        <button
          type="button"
          className={styles.chipAddBtn}
          onClick={addDraft}
          aria-label="Add mood"
          disabled={!draft.trim()}
        >
          <PlusIcon width={16} height={16} />
        </button>
      </div>
    </div>
  );
}

/* ---- Reference image drop ---- */

export function ReferenceDrop({
  value,
  onChange,
  labelledBy,
}: BaseProps & { value: ReferenceImage[] }) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addFiles = (files: FileList | File[]) => {
    const accepted: ReferenceImage[] = [];
    let rejected = 0;
    for (const file of Array.from(files)) {
      if (!file.type.startsWith("image/")) {
        rejected += 1;
        continue;
      }
      if (file.size > MAX_IMAGE_BYTES) {
        setError(`"${file.name}" is over 8 MB — try a smaller version.`);
        continue;
      }
      accepted.push({ id: uid("img"), name: file.name, src: URL.createObjectURL(file) });
    }
    if (rejected > 0 && accepted.length === 0) {
      setError("Those need to be image files (PNG, JPG, WebP, GIF).");
    } else if (accepted.length > 0) {
      setError(null);
      onChange({ kind: "references", images: [...value, ...accepted] });
    }
  };

  // Paste images from the clipboard while this step is mounted.
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const files = Array.from(e.clipboardData?.files ?? []).filter((f) =>
        f.type.startsWith("image/"),
      );
      if (files.length) {
        e.preventDefault();
        addFiles(files);
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const remove = (id: string) => {
    const img = value.find((i) => i.id === id);
    if (img) URL.revokeObjectURL(img.src);
    onChange({ kind: "references", images: value.filter((i) => i.id !== id) });
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  };

  const onFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) addFiles(e.target.files);
    e.target.value = "";
  };

  return (
    <div className={styles.refs}>
      <button
        type="button"
        className={styles.dropzone}
        data-dragging={dragging}
        aria-labelledby={labelledBy}
        onClick={() => fileInput.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <ImagesIcon className={styles.dropIcon} width={26} height={26} />
        <span className={styles.dropTitle}>Drop images, paste, or browse</span>
        <span className={styles.dropHint}>PNG, JPG, WebP or GIF — up to 8 MB each</span>
        <input
          ref={fileInput}
          type="file"
          accept="image/*"
          multiple
          className={styles.fileInput}
          onChange={onFileChange}
          tabIndex={-1}
        />
      </button>

      {error && (
        <p className={styles.refError} role="alert">
          {error}
        </p>
      )}

      {value.length > 0 && (
        <ul className={styles.thumbs}>
          {value.map((img) => (
            <li key={img.id} className={styles.thumb}>
              <img src={img.src} alt={img.name} />
              <button
                type="button"
                className={styles.thumbRemove}
                onClick={() => remove(img.id)}
                aria-label={`Remove ${img.name}`}
              >
                <CloseIcon width={14} height={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ---- Palette picker (swatches + axes) ---- */

const MAX_SWATCHES = 6;

export function PalettePicker({
  value,
  onChange,
  labelledBy,
}: BaseProps & { value: PaletteValue }) {
  const warmthId = useId();
  const intensityId = useId();

  const toggleSwatch = (id: string) => {
    const has = value.swatches.includes(id);
    if (!has && value.swatches.length >= MAX_SWATCHES) return;
    const swatches = has
      ? value.swatches.filter((s) => s !== id)
      : [...value.swatches, id];
    onChange({ kind: "palette", palette: { ...value, swatches } });
  };

  const setAxis = (axis: "warmth" | "intensity", v: number) =>
    onChange({ kind: "palette", palette: { ...value, [axis]: clamp(v, 0, 1) } });

  const axisIds = { warmth: warmthId, intensity: intensityId };

  return (
    <div className={styles.palette} aria-labelledby={labelledBy}>
      <ul className={styles.swatches} role="group" aria-label="Colour anchors">
        {SWATCHES.map((s) => {
          const selected = value.swatches.includes(s.id);
          return (
            <li key={s.id}>
              <button
                type="button"
                className={styles.swatch}
                data-selected={selected}
                style={{ "--swatch": s.hex } as React.CSSProperties}
                aria-pressed={selected}
                aria-label={s.name}
                title={s.name}
                onClick={() => toggleSwatch(s.id)}
              >
                {selected && <CheckIcon className={styles.swatchCheck} width={16} height={16} />}
              </button>
            </li>
          );
        })}
      </ul>

      <div className={styles.axes}>
        {PALETTE_AXES.map((axis) => (
          <div key={axis.id} className={styles.axis}>
            <label htmlFor={axisIds[axis.id]} className={styles.axisLabel}>
              {axis.label}
            </label>
            <div className={styles.axisTrack}>
              <span className={styles.axisEnd}>{axis.lowLabel}</span>
              <input
                id={axisIds[axis.id]}
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={value[axis.id]}
                className={styles.slider}
                onChange={(e) => setAxis(axis.id, Number(e.target.value))}
              />
              <span className={styles.axisEnd}>{axis.highLabel}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---- Dispatcher ---- */

export function AnswerInput({
  value,
  seedChips,
  onChange,
  labelledBy,
  autoFocus,
  placeholder,
}: BaseProps & {
  value: AnswerValue;
  seedChips?: string[];
  placeholder?: string;
}) {
  switch (value.kind) {
    case "text":
      return (
        <TextAnswer
          value={value.text}
          onChange={onChange}
          labelledBy={labelledBy}
          autoFocus={autoFocus}
          placeholder={placeholder}
        />
      );
    case "chips":
      return (
        <ChipChoice
          value={value.chips}
          seedChips={seedChips ?? []}
          onChange={onChange}
          labelledBy={labelledBy}
        />
      );
    case "references":
      return <ReferenceDrop value={value.images} onChange={onChange} labelledBy={labelledBy} />;
    case "palette":
      return <PalettePicker value={value.palette} onChange={onChange} labelledBy={labelledBy} />;
  }
}
