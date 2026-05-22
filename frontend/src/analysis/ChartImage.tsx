interface ChartImageProps {
  /** Data URI o URL de la imagen generada por el backend (matplotlib). */
  src: string;
  /** Texto alternativo / título del gráfico. */
  alt: string;
  /** Leyenda opcional bajo el gráfico. */
  caption?: string;
}

/**
 * Muestra un gráfico generado por el backend (matplotlib vía sandbox),
 * centrado y con leyenda. El frontend NO dibuja gráficos: solo presenta
 * lo que el modelo produjo, de modo que el backend pueda corregir o
 * adaptar el contenido sin tocar el frontend.
 */
export function ChartImage({ src, alt, caption }: ChartImageProps) {
  return (
    <figure className="chart-figure">
      <img className="chart-figure__img" src={src} alt={alt} loading="lazy" />
      {caption && <figcaption className="chart-figure__caption">{caption}</figcaption>}
    </figure>
  );
}
