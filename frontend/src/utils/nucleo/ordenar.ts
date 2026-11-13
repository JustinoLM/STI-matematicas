/** Tarjetas de la forma "ordenar": se identifican por posición original (puede haber números repetidos) */
export interface Tarjeta {
  id: string;
  valor: string;
}

export const tarjetasDesdeNumeros = (numeros: string[]): Tarjeta[] =>
  numeros.map((valor, i) => ({ id: `t${i}`, valor }));
