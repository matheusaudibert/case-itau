import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { App } from './app';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('mostra o título e os links de navegação', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;

    expect(html.querySelector('.titulo')?.textContent).toContain('Controle de Estoque');
    const links = [...html.querySelectorAll('nav a')].map((a) => a.getAttribute('href'));
    expect(links).toEqual(['/produtos', '/consulta']);
  });
});
