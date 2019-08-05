#AUTOGENERATED! DO NOT EDIT! File to edit: dev/01a_dataloader.ipynb (unless otherwise specified).

__all__ = ['DataLoader', 'Dataset', 'DataLoader']

from ..imports import *
from ..test import *
from ..core import *
from ..notebook.showdoc import show_doc

from torch.utils.data.dataloader import _MultiProcessingDataLoaderIter,_SingleProcessDataLoaderIter,_DatasetKind
_loaders = (_MultiProcessingDataLoaderIter,_SingleProcessDataLoaderIter)

def _wif(worker_id):
    info = get_worker_info()
    ds = info.dataset.d
    ds.nw,ds.offs,ds.seed = info.num_workers,info.id,info.seed
    ds.wif()

class DataLoader():
    reset = wif = noop
    _methods = 'collate indexes batches reset wif sampler'.split()
    @kwargs(_methods)
    def __init__(self, items=None, bs=None, drop_last=False, shuffle=False, indexed=None,
                 num_workers=0, pin_memory=False, timeout=0, tfm=noop, **kwargs):
        replace_methods(self, kwargs)
        if indexed is None: indexed = items is not None and hasattr(items,'__getitem__')
        store_attr(self, 'items,tfm,bs,drop_last,shuffle,indexed')
        self.dsit = _FakeLoader(self, pin_memory, num_workers, timeout)
        self.lock,self.seed,self.rng,self.nw,self.offs = Lock(),None,random.Random(),1,0
        try: self.n = len(self.items)
        except TypeError: self.n = None
        assert not kwargs or not (bs is None and drop_last)

    def __iter__(self): return self.dsit.loader()
    def _iter(self):
        if self.seed is not None: set_seed(self.seed)
        self.it = iter(self.items) if self.items else None
        self.reset()
        idxs = (b for i,b in enumerate(self.sampler()) if i%self.nw==self.offs)
        res = self.batches(iter(idxs))
        return map(self.tfm, map(self.collate, res))

    def __len__(self):
        if self.n is None: raise TypeError
        if self.bs is None: return self.n
        return self.n//self.bs + (0 if self.drop_last or self.n%self.bs==0 else 1)

    def batches(self, idxs):
        res = map(self.item, idxs)
        return res if self.bs is None else chunked(res, self.bs, self.drop_last)

    def sampler(self):
        res = Inf.count if self.indexed else Inf.nones
        if self.n is None: return res
        res = list(itertools.islice(res, self.n))
        return self.rng.sample(res,len(res)) if self.shuffle else res

    def collate(self, b): return (default_collate,default_convert)[self.bs is None](b)
    def item(self, s): return next(self.it) if s is None else self.items[s]

class Dataset():
    _methods = 'collate_fn indexes batches reset wif sampler'.split()
    @kwargs(_methods)
    def __init__(self, items=None, bs=None, drop_last=False, shuffle=False, indexed=None, **kwargs):
        if indexed is None: indexed = items is not None and hasattr(items,'__getitem__')
        self.items,self.bs,self.drop_last,self.shuffle,self.indexed = items,bs,drop_last,shuffle,indexed
        try: self.items.dataset = self
        except: pass
        self.lock,self.seed,self.rng,self.nw,self.offs = Lock(),None,random.Random(),1,0
        replace_methods(self, kwargs)
        try: self.n = len(self.items)
        except TypeError: self.n = None
        assert not kwargs or not (bs is None and drop_last)

    def __iter__(self):
        if self.seed is not None: set_seed(self.seed)
        self.it = iter(self.items) if self.items else None
        idxs = (b for i,b in enumerate(self.sampler()) if i%self.nw==self.offs)
        self.reset()
        return map(self.collate_fn, self.batches(iter(idxs)))

    def __len__(self):
        if self.n is None: raise TypeError
        if self.bs is None: return self.n
        return self.n//self.bs + (0 if self.drop_last or self.n%self.bs==0 else 1)

    def batches(self, idxs):
        res = map(self.item, idxs)
        return res if self.bs is None else chunked(res, self.bs, self.drop_last)

    def sampler(self):
        res = Inf.count if self.indexed else Inf.nones
        if self.n is None: return res
        res = list(itertools.islice(res, self.n))
        return self.rng.sample(res,len(res)) if self.shuffle else res

    reset = wif = noop
    def collate_fn(self, b): return (default_collate,default_convert)[self.bs is None](b)
    def item(self, s): return next(self.it) if s is None else self.items[s]

class DataLoader(GetAttr):
    _auto_collation,collate_fn,drop_last,dataset_kind,_index_sampler = False,noops,False,_DatasetKind.Iterable,Inf.count
    @delegates(DataLoader.__init__)
    def __init__(self, items, num_workers=0, pin_memory=False, timeout=0, tfm=noop, **kwargs):
        self.default = self.dataset = items if isinstance(items, DataLoader) else DataLoader(items, **kwargs)
        self.pin_memory,self.tfm,self.worker_init_fn = pin_memory,tfm,_wif
        self.num_workers = 0 if num_workers < 0 else num_workers
        self.timeout = 0 if timeout < 0 else timeout
        self.dataset.lock = Lock()

    def __iter__(self):  return map(self.tfm, _loaders[self.num_workers==0](self))
    def __len__(self): return len(self.dataset)