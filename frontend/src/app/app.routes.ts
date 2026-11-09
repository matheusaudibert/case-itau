import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'produtos' },
  {
    path: 'produtos',
    title: 'Produtos',
    loadComponent: () => import('./produtos/lista-produtos').then((m) => m.ListaProdutos),
  },
  {
    path: 'produtos/:produtoId',
    title: 'Produto',
    loadComponent: () => import('./produtos/produto-detalhe').then((m) => m.ProdutoDetalhe),
  },
  {
    path: 'consulta',
    title: 'Consultar reserva ou bloqueio',
    loadComponent: () => import('./consulta/consulta').then((m) => m.Consulta),
  },
  { path: '**', redirectTo: 'produtos' },
];
