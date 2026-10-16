import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {Main,TOTAL} from './Main';
const Root=()=> <Composition id="RydeResolve" component={Main} durationInFrames={TOTAL} fps={30} width={1920} height={1080}/>;
registerRoot(Root);
