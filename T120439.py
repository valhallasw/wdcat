import sys
import os
import querier
import collections

os.environ["PYWIKIBOT2_NO_USER_CONFIG"] = "1"
import pywikibot  # noqa


class WdCatTool(object):
    def __init__(self, baseQ, sourcewiki, targetwiki, verbose=False):
        self.baseQ = baseQ
        self.sourcewiki = sourcewiki
        self.targetwiki = targetwiki
        self.wdqmap = collections.defaultdict(dict)
        self.pagemap = {}
        self.target_map = {}
        self.pages_in_cat = {}
        self.cat_for_pages = collections.defaultdict(dict)
        
        self.q = querier.Querier(host='c3.labsdb', mediawiki=True, verbose=verbose)
        
    def prepare(self):
        self.sourcecat = self.get_cat(self.baseQ, self.sourcewiki)
        self.targetcat = self.get_cat(self.baseQ, self.targetwiki)
        self.sourcetree = self.build_category_tree(self.sourcecat)
        self.targettree = self.build_category_tree(self.targetcat)
        self.sourcecats = self.flatten(self.sourcetree)
        self.targetcats = self.flatten(self.targettree)
        
        for entry in self.sourcecats + self.targetcats:
            self.get_wdq(entry)
            
        self.map_target_cat_recursive(self.sourcetree)
        
        for cat in self.sourcecats + self.targetcats:
            self.pages_in_cat[cat] = self.get_pages_in_cat(cat)
            for page in self.pages_in_cat[cat]:
                self.cat_for_pages[page][self.sourcewiki] = cat
        
    @property
    def sourcesite(self):
        return pywikibot.site.APISite.fromDBName(sourcewiki)

    @property
    def targetsite(self):
        return pywikibot.site.APISite.fromDBName(targetwiki)

    def get_cat(self, item_id, site_id):
        return self.get_wdq_item(pywikibot.Category, item_id, site_id)

    def get_page(self, item_id, site_id):
        return self.get_wdq_item(pywikibot.Page, item_id, site_id)
    
    def get_wdq_item(self, typ, item_id, site_id):
        sql = """
        SELECT ips_site_page
        FROM wikidatawiki_p.wb_items_per_site
        WHERE ips_item_id=%s
        AND ips_site_id=%s;
        """
        try:
            return self.wdqmap[item_id][site_id]
        except KeyError:
            pass

        try:
            catname = q.do(sql, (item_id, site_id))[0]['ips_site_page']
            site = pywikibot.site.APISite.fromDBName(site_id)
            item = typ(site, catname)
        except IndexError:
            item = None
        
        self.wdqmap[item_id][site_id] = item
        self.pagemap[item] = item_id
        
        return item

    def get_child_categories(self, cat):
        sql = """
        SELECT page_title
        FROM {dbname}.categorylinks
        LEFT JOIN {dbname}.page
        ON cl_from=page_id
        WHERE page_namespace=14
        AND cl_to=%s
        """.format(dbname=cat.site.dbName() + "_p")
        subcats = q.do(sql, [cat.title(underscore=True, withNamespace=False,)])
        subcats = [x["page_title"] for x in subcats]
        subcats = [pywikibot.Category(cat.site, x) for x in subcats]
        return subcats
    
    def build_category_tree_recursor(self, sourcecat, maxlevel=10):
        if maxlevel == 0:
            raise Exception('Maximum category depth reached')
        return {cat: self.build_category_tree_recursor(cat, maxlevel=maxlevel-1)
                for cat in self.get_child_categories(sourcecat)}
                    
    def build_category_tree(self, sourcecat, maxlevel=10):
        return {sourcecat: self.build_category_tree_recursor(sourcecat, maxlevel=maxlevel-1)}
    
    # now we build a mapping from categories to wikidata and vice versa
    def flatten(self, tree):
        out = tree.keys()
        for subtree in tree.values():
            out = out + flatten(subtree)
        return out

    def get_wdq(self, cat):
        sql = """
        SELECT ips_item_id
        FROM wikidatawiki_p.wb_items_per_site
        WHERE ips_site_id=%s
        AND ips_site_page=%s;
        """
        if cat in self.pagemap:
            return self.pagemap[cat]
        try:
            Q = q.do(sql, (cat.site.dbName(), cat.title()))[0]['ips_item_id']
        except IndexError:
            Q = None
        
        if Q is not None:
            self.wdqmap[Q][cat.site.dbName()] = cat
        self.pagemap[cat] = Q
        return self.pagemap[cat]
    
    # now, map each source category to a target category
    def get_target_category(self, sourcecat, sourceparent):
        try:
            target = self.wdqmap[self.pagemap[sourcecat]][self.targetwiki]
        except KeyError as e:
            print repr(e)
            target = None  # I guess? not entirely obvious.
        self.target_map[sourcecat] = target if target is not None else self.target_map[sourceparent]
        return self.target_map[sourcecat]
        
    # traverse the tree recursively
    def map_target_cat_recursive(self, tree, parent=None):
        for k,v in tree.iteritems():
            self.get_target_category(k, parent)
            self.map_target_cat_recursive(v, parent=k)

    # we now want to enumerate pages in any of the source categories
    # and for each, note what the most suitable category is

    def get_pages_in_cat(self, cat):
        sql = """
        SELECT page_title
        FROM {dbname}.categorylinks
        LEFT JOIN {dbname}.page
        ON cl_from=page_id
        WHERE page_namespace=0
        AND cl_to=%s
        """.format(dbname=cat.site.dbName() + "_p")
        pages = q.do(sql, [cat.title(underscore=True, withNamespace=False,)])
        pages = [x["page_title"] for x in pages]
        pages = [pywikibot.Page(cat.site, x) for x in pages]
        
        for page in pages:
            Q = self.get_wdq(page)
            self.get_page(Q, self.targetwiki)

        return pages

    # now print the tree for source, and show target categories
    def print_tree_and_pages_recursive(self, tree, depth=0):
        titlekwargs = dict(asLink=True, textlink=True, insite=targetsite)
        for scat,v in tree.iteritems():
            tcat = self.target_map[scat]
            print u"{:<60}: {}".format("*"*(depth+1) + "'''" + scat.title(**titlekwargs), tcat.title(**titlekwargs) + "'''")
            
            pages = [(p, self.wdqmap[self.pagemap[p]][self.targetwiki]) for p in self.pages_in_cat[scat]]
            pages = [x for x in pages if x[1] is not None]
            
            for s,t in pages:
                if t is not None:
                    # check if t is already categorized correctly
                    if self.cat_for_pages[t] == tcat:
                        pass
                    print "*"*(depth+2) + u"{:<50}: {:<50}".format(s.title(**titlekwargs), t.title(**titlekwargs))
            self.print_tree_and_pages_recursive(v, depth=depth+1)
    
    def print_tree(self):
        self.print_tree_and_pages_recursive(self.sourcetree)
        
        
if __name__ == "__main__":
    wct = WdCatTool(9649201, 'plwiki', 'enwiki', verbose=True)
    wct.prepare()
    wct.print_tree()