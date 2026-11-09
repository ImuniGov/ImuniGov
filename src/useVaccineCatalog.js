import { useEffect, useState } from "react";
import { api } from "./api";
import { vaccines } from "./format";

export function useVaccineCatalog() {
  const [catalog, setCatalog] = useState(null);
  useEffect(() => {
    let active = true;
    api("/api/v1/vaccine-catalog")
      .then((result) => {
        if (active) setCatalog(result);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  return {
    catalog,
    names: catalog
      ? [...new Set([...vaccines, ...catalog.items.map((i) => i.name)])]
      : vaccines,
  };
}
