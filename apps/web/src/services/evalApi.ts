import { createEvalApi } from '@scholar-ai/sdk';
import { sdkHttpClient } from './sdkHttpClient';

export const evalApi = createEvalApi(sdkHttpClient);
