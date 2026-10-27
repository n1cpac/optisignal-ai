import { ApplicationConfig } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';

import { USE_MOCK_API } from './core/mock-api.config';
import { mockApiInterceptor } from './core/interceptors/mock-api.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(
      ...(USE_MOCK_API ? [withInterceptors([mockApiInterceptor])] : [])
    )
  ]
};
