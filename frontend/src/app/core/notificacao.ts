import { Injectable, inject } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

import { mensagemDeErro } from './mensagem-erro';

@Injectable({ providedIn: 'root' })
export class Notificacao {
  private readonly snackBar = inject(MatSnackBar);

  sucesso(mensagem: string): void {
    this.snackBar.open(mensagem, 'OK', { duration: 3000, panelClass: 'notificacao-sucesso' });
  }

  erro(erro: unknown): void {
    this.snackBar.open(mensagemDeErro(erro), 'Fechar', {
      duration: 6000,
      panelClass: 'notificacao-erro',
    });
  }
}
