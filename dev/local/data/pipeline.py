#AUTOGENERATED! DO NOT EDIT! File to edit: dev/02a_pipeline.ipynb (unless otherwise specified).

__all__ = ['get_func', 'Func', 'Sig', 'SelfFunc', 'Self', 'compose_tfms', 'batch_to_samples', 'mk_transform',
           'Pipeline', 'TfmdList', 'TfmdDS']

from ..imports import *
from ..test import *
from ..core import *
from .transform import *
from ..notebook.showdoc import show_doc

def get_func(t, name, *args, **kwargs):
    "Get the `t.name` (potentially partial-ized with `args` and `kwargs`) or `noop` if not defined"
    f = getattr(t, name, noop)
    return f if not (args or kwargs) else partial(f, *args, **kwargs)

class Func():
    "Basic wrapper around a `name` with `args` and `kwargs` to call on a given type"
    def __init__(self, name, *args, **kwargs): self.name,self.args,self.kwargs = name,args,kwargs
    def __repr__(self): return f'sig: {self.name}({self.args}, {self.kwargs})'
    def _get(self, t): return get_func(t, self.name, *self.args, **self.kwargs)
    def __call__(self,t): return L(t).mapped(self._get) if is_listy(t) else self._get(t)

class _Sig():
    def __getattr__(self,k):
        def _inner(*args, **kwargs): return Func(k, *args, **kwargs)
        return _inner

Sig = _Sig()

class SelfFunc():
    "Search for `name` attribute and call it with `args` and `kwargs` on any object it's passed."
    def __init__(self, nm, *args, **kwargs): self.nm,self.args,self.kwargs = nm,args,kwargs
    def __repr__(self): return f'self: {self.nm}({self.args}, {self.kwargs})'
    def __call__(self, o):
        if not is_listy(o): return getattr(o,self.nm)(*self.args, **self.kwargs)
        else: return [getattr(o_,self.nm)(*self.args, **self.kwargs) for o_ in o]

class _SelfFunc():
    def __getattr__(self,k):
        def _inner(*args, **kwargs): return SelfFunc(k, *args, **kwargs)
        return _inner

Self = _SelfFunc()

def compose_tfms(x, tfms, is_enc=True, reverse=False, **kwargs):
    "Apply all `func_nm` attribute of `tfms` on `x`, maybe in `reverse` order"
    if reverse: tfms = reversed(tfms)
    for f in tfms:
        if not is_enc: f = f.decode
        x = f(x, **kwargs)
    return x

def batch_to_samples(b, max_rows=10):
    "'Transposes' a batch to (at most `max_rows`) samples"
    if isinstance(b, Tensor): return b[:max_rows]
    return zip(*L(batch_to_samples(b_, max_rows) for b_ in b))

def mk_transform(f, as_item=True):
    "Convert function `f` to `Transform` if it isn't already one"
    return f if isinstance(f,Transform) else Transform(f, as_item=as_item)

class Pipeline():
    "A pipeline of composed (for encode/decode) transforms, setup with types"
    def __init__(self, funcs=None, as_item=True):
        if not funcs: funcs=[noop]
        if isinstance(funcs, Pipeline): funcs = funcs.fs
        self.fs = L(funcs).mapped(mk_transform).sorted(key='order')
        self.set_as_item(as_item)

    def set_as_item(self, as_item):
        self.as_item = as_item
        for f in self.fs: f.as_item = as_item

    def setup(self, items=None):
        tfms,self.fs = self.fs,[]
        for t in tfms: self.add(t,items)

    def add(self,t, items=None):
        getattr(t, 'setup', noop)(items)
        self.fs.append(t)

    def __call__(self, o, filt=None): return compose_tfms(o, tfms=self.fs, filt=filt)
    def decode  (self, o, filt=None): return compose_tfms(o, tfms=self.fs, is_enc=False, reverse=True, filt=filt)
    def __repr__(self): return f"Pipeline: {self.fs}"
    def __getitem__(self,i): return self.fs[i]
    def decode_batch(self, b, filt=None, max_rows=10):
        return [self.decode(b_, filt=filt) for b_ in batch_to_samples(b, max_rows=max_rows)]

    # TODO: move show_batch here of TfmDS?
    def show(self, o, ctx=None, filt=None, **kwargs):
        for f in reversed(self.fs):
            res = self._show(o, ctx, **kwargs)
            if res: return res
            o = f.decode(o, filt=filt)
        return self._show(o, ctx, **kwargs)

    def _show(self, o, ctx, **kwargs):
        o1 = [o] if self.as_item else o
        if not all(hasattr(o_, 'show') for o_ in o1): return
        for o_ in o1: ctx = o_.show(ctx=ctx, **kwargs)
        return ctx or 1

class TfmdList():
    "A `Pipeline` of `tfms` applied to a collection of `items`"
    def __init__(self, items, tfms, do_setup=True, as_item=True):
        self.items = L(items)
        self._mk_pipeline(tfms.tfms if isinstance(tfms,TfmdList) else tfms, do_setup=do_setup, as_item=as_item)

    def _mk_pipeline(self, tfms, do_setup, as_item):
        if isinstance(tfms,Pipeline): self.tfms = tfms
        else:
            self.tfms = Pipeline(tfms, as_item=as_item)
            if do_setup: self.setup()

    def __getitem__(self, i): return self.get(i)
    def get(self, i, filt=None):
        "Transformed item(s) at `i`"
        its = self.items[i]
        if is_iter(i): return L(self._get(it, filt=filt) for it in its)
        return self._get(its, filt=filt)

    def _get(self, it, filt=None): return self.tfms(it, filt=filt)

    def subset(self, idxs): return self.__class__(self.items[idxs], self.tfms, do_setup=False)
    def decode_at(self, idx, filt=None): return self.decode(self.get(idx,filt=filt), filt=filt)
    def show_at(self, idx, filt=None, **kwargs): return self.show(self.get(idx,filt=filt), filt=filt, **kwargs)

    def decode_batch(self, b, filt=None, max_rows=10):
        return [self.decode(b_, filt=filt) for b_ in batch_to_samples(b, max_rows=max_rows)]

    # Standard dunder magics
    def __eq__(self, b): return all_equal(self, b)
    def __len__(self): return len(self.items)
    def __iter__(self): return (self[i] for i in range_of(self))
    def __repr__(self): return f"{self.__class__.__name__}: {self.items}\ntfms - {self.tfms.fs}"

    # Delegating to `self.tfms`
    def show(self, o, **kwargs): return self.tfms.show(o, **kwargs)
    def setup(self): self.tfms.setup(self)
    def decode(self, x, **kwargs): return self.tfms.decode(x, **kwargs)
    def __call__(self, x, **kwargs): return self.tfms.__call__(x, **kwargs)


@docs
class TfmdDS(TfmdList):
    "A dataset that creates a tuple from each `type_tfms`, passed thru `ds_tfms`"
    def __init__(self, items, type_tfms=None, ds_tfms=None, do_setup=True):
        self.items = L(items)
        self.tls = [TfmdList(items, t, do_setup=do_setup) for t in L(type_tfms)]
        self._mk_pipeline(ds_tfms, do_setup=do_setup, as_item=False)

    def _get(self, it, filt=None):
        o = tuple(tl._get(it, filt=filt) for tl in self.tls)
        return self.tfms(o, filt=filt)

    def decode(self, o, filt=None):
        o = self.tfms.decode(o, filt=filt)
        return tuple(it.decode(o_, filt=filt) for o_,it in zip(o,self.tls))

    def show(self, o, ctx=None, filt=None, **kwargs):
        # Currently we don't support showing at tuple level, so we just decode all tfms at once
        o = super().decode(o, filt=filt)
        for o_,it in zip(o,self.tls): ctx = it.show(o_, ctx=ctx, filt=filt, **kwargs)
        return ctx

    def setup(self): self.tfms.setup(self)
    def subset(self, idxs): return self.__class__(self.items[idxs], self.tls, self.tfms, do_setup=False)
    def __repr__(self): return f"{self.__class__.__name__}: tls - {self.tls}\nds tfms - {self.tfms}"

    _docs=dict(
        get="Call all `tfms` on `items[i]` then all `tuple_tfms` on the result",
        decode="Compose `decode` of all `tuple_tfms` then all `tfms` on `i`",
        show="Show item `o` in `ctx`",
        subset="New `TfmdDS` that only includes items at `idxs`",
        setup="Go through the transforms in order and call their potential setup on `items`")