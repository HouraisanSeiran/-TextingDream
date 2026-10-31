import { useEffect, useState } from 'react';
import { listNativeWorlds, readNativeWorld, type NativeWorld, type NativeWorldRow } from './bridge';
import { errorMessage } from './hostApi';

/** Each request owns its lifetime. Old success AND failure cannot replace a newer selection. */
export function useNativeWorlds(author: boolean) {
  const [worlds, setWorlds] = useState<NativeWorldRow[]>([]);
  const [importId, setImportId] = useState<string | null>(null);
  const [source, setSource] = useState<{ id: string; world: NativeWorld } | null>(null);
  const [listing, setListing] = useState(author);
  const [reading, setReading] = useState(false);
  const [listError, setListError] = useState('');
  const [readError, setReadError] = useState('');
  const [listAttempt, setListAttempt] = useState(0);
  const [readAttempt, setReadAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setWorlds([]); setImportId(null); setListError(''); setListing(author);
    if (author) void listNativeWorlds().then(rows => {
      if (!active) return;
      setWorlds(rows);
      setImportId(rows.at(-1)?.importId ?? null);
    }).catch(error => { if (active) setListError(errorMessage(error)); })
      .finally(() => { if (active) setListing(false); });
    return () => { active = false; };
  }, [author, listAttempt]);

  useEffect(() => {
    let active = true;
    setSource(null); setReadError(''); setReading(author && !!importId);
    if (author && importId) void readNativeWorld(importId).then(world => {
      if (active) setSource({ id: importId, world });
    }).catch(error => { if (active) setReadError(errorMessage(error)); })
      .finally(() => { if (active) setReading(false); });
    return () => { active = false; };
  }, [author, importId, readAttempt]);

  return {
    worlds, setWorlds, importId, setImportId,
    loaded: author && source?.id === importId ? source.world : null,
    busy: author && (listing || reading), error: author ? listError || readError : '',
    retry: () => listError ? setListAttempt(n => n + 1) : setReadAttempt(n => n + 1),
  };
}
