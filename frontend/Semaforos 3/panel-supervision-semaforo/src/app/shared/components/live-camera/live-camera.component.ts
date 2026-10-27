import {
  AfterViewInit,
  Component,
  ElementRef,
  Input,
  OnDestroy,
  ViewChild,
  signal
} from '@angular/core';

type EstadoCamara = 'iniciando' | 'activa' | 'error';

/**
 * Muestra una camara en vivo usando getUserMedia.
 * Busca el dispositivo cuyo nombre contenga `etiquetaDispositivo` (por defecto "OBS",
 * la camara virtual de OBS). Si no la encuentra, usa la camara predeterminada.
 */
@Component({
  selector: 'app-live-camera',
  standalone: true,
  template: `
    <div class="camara">
      <video #video muted playsinline></video>

      @if (estado() === 'iniciando') {
        <p class="mensaje">Conectando con la cámara...</p>
      }
      @if (estado() === 'error') {
        <div class="mensaje error">
          <p>{{ error() }}</p>
          <button type="button" (click)="iniciarCamara()">Reintentar</button>
        </div>
      }
      @if (estado() === 'activa') {
        <span class="etiqueta">{{ nombreDispositivo() }}</span>
      }
    </div>
  `,
  styles: [`
    .camara { position: relative; background: #000; min-height: 160px; }
    video { display: block; width: 100%; height: auto; }
    .mensaje {
      position: absolute; inset: 0; margin: 0; padding: 12px;
      display: flex; flex-direction: column; gap: 8px; align-items: center; justify-content: center;
      text-align: center; font-size: 13px; color: #fff;
    }
    .mensaje p { margin: 0; }
    .mensaje.error { background: rgba(0, 0, 0, 0.8); }
    button { padding: 6px 12px; font: inherit; border: 2px solid #1e6fff; background: #222; color: #fff; cursor: pointer; }
    .etiqueta { position: absolute; left: 6px; bottom: 6px; padding: 2px 6px; font-size: 11px; background: rgba(0, 0, 0, 0.6); color: #fff; }
  `]
})
export class LiveCameraComponent implements AfterViewInit, OnDestroy {
  /** Texto que debe contener el nombre de la camara (sin distinguir mayusculas). */
  @Input() etiquetaDispositivo = 'OBS';

  @ViewChild('video', { static: true }) video!: ElementRef<HTMLVideoElement>;

  protected estado = signal<EstadoCamara>('iniciando');
  protected error = signal('');
  protected nombreDispositivo = signal('');

  private stream?: MediaStream;
  private destruido = false;
  private iniciando = false;

  /**
   * Si cambia la lista de camaras (por ejemplo, se inicia la camara virtual de OBS despues de abrir
   * el panel), reintenta. Con la camara de OBS ya activa no hace nada, y si se esta usando otra
   * camara solo cambia cuando aparece la de OBS.
   */
  private alCambiarDispositivos = async () => {
    if (this.iniciando) return;
    if (this.estado() === 'activa') {
      if (this.esObs()) return;
      const dispositivos = await navigator.mediaDevices.enumerateDevices();
      if (!this.buscarObs(dispositivos)) return;
    }
    this.iniciarCamara();
  };

  ngAfterViewInit(): void {
    this.iniciarCamara();
    navigator.mediaDevices?.addEventListener('devicechange', this.alCambiarDispositivos);
  }

  ngOnDestroy(): void {
    this.destruido = true;
    navigator.mediaDevices?.removeEventListener('devicechange', this.alCambiarDispositivos);
    this.detener();
  }

  async iniciarCamara(): Promise<void> {
    if (this.iniciando) return;
    this.iniciando = true;
    this.estado.set('iniciando');
    this.detener();

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Este navegador no permite acceder a la cámara (se necesita localhost o HTTPS).');
      }

      // Se pide permiso primero para que el navegador muestre los nombres de las camaras
      const temporal = await navigator.mediaDevices.getUserMedia({ video: true });
      temporal.getTracks().forEach((t) => t.stop());

      const dispositivos = await navigator.mediaDevices.enumerateDevices();
      const obs = this.buscarObs(dispositivos);

      const stream = await navigator.mediaDevices.getUserMedia({
        video: obs ? { deviceId: { exact: obs.deviceId } } : true
      });

      // Si el componente se destruyo mientras se esperaba, se libera la camara
      if (this.destruido) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }

      this.stream = stream;
      this.nombreDispositivo.set(stream.getVideoTracks()[0]?.label ?? '');
      const elemento = this.video.nativeElement;
      elemento.srcObject = stream;
      await elemento.play();
      this.estado.set('activa');
    } catch (e) {
      if (!this.destruido) {
        this.detener();
        this.error.set(this.mensajeDeError(e));
        this.estado.set('error');
      }
    } finally {
      this.iniciando = false;
    }
  }

  private buscarObs(dispositivos: MediaDeviceInfo[]): MediaDeviceInfo | undefined {
    const buscada = this.etiquetaDispositivo.toLowerCase();
    return dispositivos.find(
      (d) => d.kind === 'videoinput' && d.label.toLowerCase().includes(buscada)
    );
  }

  private esObs(): boolean {
    return this.nombreDispositivo().toLowerCase().includes(this.etiquetaDispositivo.toLowerCase());
  }

  private detener(): void {
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = undefined;
    this.video.nativeElement.srcObject = null;
  }

  private mensajeDeError(e: unknown): string {
    const nombre = e instanceof DOMException ? e.name : '';
    switch (nombre) {
      case 'NotAllowedError':
        return 'El navegador no tiene permiso para usar la cámara. Permítelo en el candado de la barra de direcciones.';
      case 'NotFoundError':
        return 'No se encontró ninguna cámara. Si usas OBS, inicia la cámara virtual.';
      case 'NotReadableError':
        return 'La cámara no está disponible o la está usando otra aplicación.';
      default:
        return e instanceof Error ? e.message : 'No se pudo iniciar la cámara.';
    }
  }
}
