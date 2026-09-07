"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, Input, Modal } from "@/design-system/primitives";
import { importClientCsv, type ImportPreview } from "@/features/workspace/api/directory-api";

export function ClientImport(): JSX.Element {
  const cache = useQueryClient();
  const [open, setOpen] = useState(false);
  const [csv, setCsv] = useState("");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [message, setMessage] = useState("");
  const mutation = useMutation({ mutationFn: (commit: boolean) => importClientCsv(csv, commit), onSuccess: (result, commit) => {
    setPreview(result);
    if (commit) { setMessage(`Импортировано клиентов: ${result.created}. Дубликаты пропущены: ${result.duplicates}.`); setCsv(""); void cache.invalidateQueries({ queryKey: ["clients"] }); }
  } });
  return <>
    <Button variant="secondary" onClick={() => setOpen(true)}>Импорт CSV</Button>
    <Modal open={open} onOpenChange={setOpen} title="Импорт клиентов" description="До 500 строк, UTF-8. Колонки: name, phone, email, source, comment. Поддерживаются запятая и точка с запятой.">
      <div className="space-y-3">
        <a download="clients-template.csv" href={'data:text/csv;charset=utf-8,' + encodeURIComponent('\ufeffname;phone;email;source;comment\r\n') } className="text-primary underline">Скачать шаблон</a>
        <Input aria-label="CSV с клиентами" type="file" accept=".csv,text/csv" onChange={async event => {
          const file = event.target.files?.[0]; setPreview(null); setMessage(""); mutation.reset();
          if (!file) return;
          if (file.size > 1024 * 1024) { setMessage("Файл должен быть меньше 1 МБ"); setCsv(""); return; }
          setCsv(await file.text());
        }} />
        <Button disabled={!csv} loading={mutation.isPending} onClick={() => mutation.mutate(false)}>Проверить файл</Button>
        {mutation.error && <p role="alert" className="text-error">{mutation.error.message}</p>}
        {message && <p role="status">{message}</p>}
        {preview && <>
          <p>Готовы: {preview.ready} · Дубликаты: {preview.duplicates} · Ошибки: {preview.invalid}</p>
          <div className="max-h-80 overflow-auto"><table className="w-full text-left text-sm"><thead><tr><th>Строка</th><th>Клиент</th><th>Проверка</th></tr></thead><tbody>{preview.rows.map(row => <tr key={row.row} className="border-t border-neutral-200"><td>{row.row}</td><td>{row.data.name}<br />{row.data.phone}</td><td className={row.status === "invalid" ? "text-error" : ""}>{row.message}</td></tr>)}</tbody></table></div>
          <p className="text-sm text-neutral-600">Будут добавлены только новые клиенты. Совпадения по телефону пропускаются. При ошибочных строках импорт недоступен.</p>
          <Button disabled={!csv || !preview.ready || preview.invalid > 0} loading={mutation.isPending} onClick={() => mutation.mutate(true)}>Импортировать {preview.ready} клиентов</Button>
        </>}
      </div>
    </Modal>
  </>;
}
