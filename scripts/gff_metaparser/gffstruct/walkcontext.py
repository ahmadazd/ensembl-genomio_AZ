import copy

class WalkContext:
  def __init__(self, tag = "", global_context = None, ctg_len_inferer = None):
    self.data = dict()
    self._tag = tag
    self.global_context = global_context
    self.ctg_len = ctg_len_inferer
    self.processed_rules = []
    self.prev = []
    self._top = None
    self._useful_leaves = []

  def snap(self):
    # shallow data copy
    self.prev.append(copy.copy(self.data))
    return self.prev[-1]

  def top(self, *feature):
    if len(feature) == 0:
      return self._top
    if feature[0]:
      self._top = feature[0]

  def tag(self, *val):
    if len(val) == 0:
      return self._tag
    self._tag = str(val[0])

  def update(self, *key_val, force_clean=False, **kwargs):
    # can have either dict as key or string with non-empty val
    if len(key_val) == 1 and isinstance(key_val[0], dict):
      for k, v in key_val[0].items():
        self.update(k,v, force_clean = force_clean)
    elif len(key_val) == 2:
      key, val = key_val
      if val is not None:
        self.data[key] = val
      elif force_clean and key in self.data:
        del self.data[key]
    # update from **kwargs
    for k, v in kwargs.items():
      self.update(k,v, force_clean = force_clean)

  def get(self, key, default = None):
    # global ???
    if key not in self.data:
      return default
    return self.data[key]

  def __getitem__(self, key):
    return self.get(key)

  def update_processed_rules(self, lst):
    self.processed_rules += lst

  def used_leaves(self, *leaves):
    if len(leaves) == 0:
      return copy.copy(self._useful_leaves)
    self._useful_leaves += leaves

  def add_fix(self, fix):
    pass

  def merge_fixes(self):
    pass

  def update_ctg_len(self, length):
   if self.ctg_len is not None:
     self.ctg_len(length)

  def get_to_root(self, getter=None):
    if not getter:
      return None
    res = []
    it = self.data
    while it:
      out = getter(it)
      if out:
        res.append(out)
        it = it.get("_PARENTCTX")
    return res[::-1]

  def run_to_root(self, updater=None):
    if not updater:
      return
    it = self.data
    while it:
      updater(it)
      it = it.get("_PARENTCTX")
    return

